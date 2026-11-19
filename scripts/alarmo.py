#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["websockets>=12"]
# ///
"""Manage Alarmo (HACS alarm integration) on Home Assistant from the command line.

Reads via the HA websocket (alarmo/* commands), writes via Alarmo's REST endpoints (/api/alarmo/*).
Needs HA_URL and HA_TOKEN (admin long-lived token). Output is JSON.

  status                                  panels, state, open/bypassed sensors, modes, sensors, actions, users
  config [--set JSON]                     global config (code requirements, trigger behaviour, MQTT, master panel)
  area [AREA_ID] [--set JSON]             one area; --set merges {"name": ..., "modes": {"armed_away": {...}}}
  sensors list | candidates
  sensors add ENTITY [--type T] [--modes a,b] [--area ID] [--set JSON]   defaults from the sensor's device_class
  sensors update ENTITY JSON | sensors remove ENTITY
  actions list | actions enable ID | actions disable ID | actions remove ID
  actions add JSON                        raw Alarmo automation (name, type, triggers, actions, enabled)
  actions sirens ENTITY [--enable]        create "on at trigger" + "off at disarm" actions for a siren entity/group
  users list | users update USER_ID JSON | users remove USER_ID
  users add NAME [--admin]                prompts for the code on the terminal (run it yourself; codes never
                                          pass through the agent)
  arm MODE [--code-env VAR] [--force] [--skip-delay]   MODE: away | home | night | vacation | custom
  disarm [--code-env VAR]

Writes print {"success": true, ...}. Nothing is armed unless you run `arm`.
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

import websockets

ARM_MODES = ["armed_away", "armed_home", "armed_night", "armed_custom_bypass", "armed_vacation"]
MODE_ALIASES = {"away": "armed_away", "home": "armed_home", "night": "armed_night",
                "vacation": "armed_vacation", "custom": "armed_custom_bypass"}

# device_class -> (alarmo sensor type, defaults). Mirrors Alarmo's own UI defaults closely.
SENSOR_DEFAULTS = {
    "door": "door", "garage_door": "door", "opening": "door",
    "window": "window",
    "motion": "motion", "occupancy": "motion", "presence": "motion", "moving": "motion",
    "tamper": "tamper", "vibration": "tamper",
    "smoke": "environmental", "gas": "environmental", "carbon_monoxide": "environmental",
    "moisture": "environmental", "heat": "environmental",
}
TYPE_DEFAULTS = {
    "door": {"modes": ["armed_away", "armed_home", "armed_night", "armed_vacation"], "use_exit_delay": True,
             "use_entry_delay": True, "always_on": False},
    "window": {"modes": ["armed_away", "armed_home", "armed_night", "armed_vacation"], "use_exit_delay": False,
               "use_entry_delay": False, "always_on": False},
    "motion": {"modes": ["armed_away", "armed_vacation"], "use_exit_delay": True, "use_entry_delay": True,
               "always_on": False},
    "tamper": {"modes": ["armed_away", "armed_home", "armed_night", "armed_vacation"], "use_exit_delay": False,
               "use_entry_delay": False, "always_on": False},
    "environmental": {"modes": [], "use_exit_delay": False, "use_entry_delay": False, "always_on": True},
    "other": {"modes": ["armed_away", "armed_vacation"], "use_exit_delay": True, "use_entry_delay": True,
              "always_on": False},
}


class HA:
    def __init__(self, url: str, token: str):
        self.http = url.rstrip("/")
        self.ws_url = re.sub(r"^http", "ws", self.http) + "/api/websocket"
        self.token = token
        self.n = 0

    async def __aenter__(self):
        self.ws = await websockets.connect(self.ws_url, max_size=64 * 1024 * 1024)
        await self.ws.recv()
        await self.ws.send(json.dumps({"type": "auth", "access_token": self.token}))
        if json.loads(await self.ws.recv()).get("type") != "auth_ok":
            raise SystemExit("auth failed")
        return self

    async def __aexit__(self, *exc):
        await self.ws.close()

    async def ws_call(self, type_: str, **kw):
        self.n += 1
        await self.ws.send(json.dumps({"id": self.n, "type": type_, **kw}))
        while True:
            msg = json.loads(await self.ws.recv())
            if msg.get("id") == self.n and msg.get("type") == "result":
                if not msg.get("success"):
                    raise SystemExit(f"{type_}: {msg.get('error')}")
                return msg["result"]

    def post(self, path: str, body: dict):
        req = urllib.request.Request(
            f"{self.http}{path}", data=json.dumps(body).encode(), method="POST",
            headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                text = resp.read().decode()
                return json.loads(text) if text else {"success": True}
        except urllib.error.HTTPError as err:
            raise SystemExit(f"POST {path}: HTTP {err.code} {err.read().decode()[:500]}")


async def _areas(ha):
    return await ha.ws_call("alarmo/areas")


async def _default_area(ha, area_id=None):
    areas = await _areas(ha)
    if area_id:
        if area_id not in areas:
            raise SystemExit(f"unknown area {area_id}; areas: {list(areas)}")
        return area_id
    if len(areas) != 1:
        raise SystemExit(f"several areas, pass --area: {[(k, v['name']) for k, v in areas.items()]}")
    return next(iter(areas))


async def _panels(ha):
    states = await ha.ws_call("get_states")
    ents = await ha.ws_call("alarmo/entities")
    ids = {e["entity_id"] for e in ents} if isinstance(ents, list) else set()
    out = []
    for s in states:
        if s["entity_id"].startswith("alarm_control_panel.") and (s["entity_id"] in ids or "arm_mode" in s["attributes"]):
            out.append(s)
    return out, {s["entity_id"]: s for s in states}


async def cmd_status(ha, a):
    panels, states = await _panels(ha)
    sensors = await ha.ws_call("alarmo/sensors")
    autos = await ha.ws_call("alarmo/automations")
    users = await ha.ws_call("alarmo/users")
    return {
        "panels": [{"entity_id": p["entity_id"], "state": p["state"],
                    "area_id": p["attributes"].get("area_id"),
                    "open_sensors": p["attributes"].get("open_sensors"),
                    "bypassed_sensors": p["attributes"].get("bypassed_sensors"),
                    "changed_by": p["attributes"].get("changed_by"),
                    "last_triggered": p["attributes"].get("last_triggered")} for p in panels],
        "config": await ha.ws_call("alarmo/config"),
        "areas": await _areas(ha),
        "sensors": [{"entity_id": k, "state": states.get(k, {}).get("state"), "type": v["type"],
                     "modes": v["modes"], "enabled": v["enabled"], "always_on": v["always_on"],
                     "entry_delay": v["use_entry_delay"], "exit_delay": v["use_exit_delay"], "area": v["area"]}
                    for k, v in sensors.items()],
        "actions": [{"id": k, "name": v["name"], "type": v["type"], "enabled": v["enabled"],
                     "triggers": v["triggers"], "actions": v["actions"]} for k, v in autos.items()],
        "users": [{"user_id": k, "name": v["name"], "enabled": v["enabled"], "can_arm": v["can_arm"],
                   "can_disarm": v["can_disarm"], "is_override_code": v["is_override_code"]}
                  for k, v in users.items()],
    }


async def cmd_sensors(ha, a):
    sub = a.rest[0] if a.rest else "list"
    sensors = await ha.ws_call("alarmo/sensors")
    if sub == "list":
        return sensors
    if sub == "candidates":
        states = await ha.ws_call("get_states")
        out = []
        for s in states:
            if not s["entity_id"].startswith("binary_sensor.") or s["entity_id"] in sensors:
                continue
            dc = s["attributes"].get("device_class")
            if dc in SENSOR_DEFAULTS:
                out.append({"entity_id": s["entity_id"], "name": s["attributes"].get("friendly_name"),
                            "device_class": dc, "suggested_type": SENSOR_DEFAULTS[dc], "state": s["state"]})
        return sorted(out, key=lambda x: (x["suggested_type"], x["entity_id"]))
    if sub == "add":
        entity = a.rest[1]
        if entity in sensors:
            raise SystemExit(f"{entity} is already an Alarmo sensor; use `sensors update`")
        states = {s["entity_id"]: s for s in await ha.ws_call("get_states")}
        if entity not in states:
            raise SystemExit(f"unknown entity {entity}")
        stype = a.type or SENSOR_DEFAULTS.get(states[entity]["attributes"].get("device_class"), "other")
        body = {"entity_id": entity, "type": stype, "area": await _default_area(ha, a.area), "enabled": True,
                "arm_on_close": False, "allow_open": False, "trigger_unavailable": False, "auto_bypass": False,
                **TYPE_DEFAULTS[stype]}
        if a.modes:
            body["modes"] = [MODE_ALIASES.get(m, m) for m in a.modes.split(",")]
        if a.set:
            body.update(json.loads(a.set))
        ha.post("/api/alarmo/sensors", body)
        return (await ha.ws_call("alarmo/sensors")).get(entity)
    if sub == "update":
        entity, changes = a.rest[1], json.loads(a.rest[2])
        if entity not in sensors:
            raise SystemExit(f"{entity} is not an Alarmo sensor")
        ha.post("/api/alarmo/sensors", {"entity_id": entity, **changes})
        return (await ha.ws_call("alarmo/sensors")).get(entity)
    if sub == "remove":
        ha.post("/api/alarmo/sensors", {"entity_id": a.rest[1], "remove": True})
        return {"removed": a.rest[1]}
    raise SystemExit(f"unknown sensors subcommand {sub}")


def _automation_body(v: dict) -> dict:
    return {k: v[k] for k in ("name", "type", "triggers", "actions", "enabled") if k in v}


async def cmd_actions(ha, a):
    sub = a.rest[0] if a.rest else "list"
    autos = await ha.ws_call("alarmo/automations")
    if sub == "list":
        return autos
    if sub in ("enable", "disable"):
        aid = a.rest[1]
        if aid not in autos:
            raise SystemExit(f"unknown action {aid}")
        body = _automation_body(autos[aid])
        body["enabled"] = sub == "enable"
        ha.post("/api/alarmo/automations", {"automation_id": aid, **body})
        return (await ha.ws_call("alarmo/automations"))[aid]
    if sub == "remove":
        ha.post("/api/alarmo/automations", {"automation_id": a.rest[1], "remove": True})
        return {"removed": a.rest[1]}
    if sub == "add":
        ha.post("/api/alarmo/automations", json.loads(a.rest[1]))
        time.sleep(1.1)  # Alarmo ids are unix seconds: two creates in one second overwrite each other
        return await ha.ws_call("alarmo/automations")
    if sub == "sirens":
        entity = a.rest[1]
        area = await _default_area(ha, a.area)
        created = []
        for name, event, service in (
            (f"Sirens on when alarm triggers ({entity})", "trigger", "homeassistant.turn_on"),
            (f"Sirens off on disarm ({entity})", "disarm", "homeassistant.turn_off"),
        ):
            if any(v["name"] == name for v in autos.values()):
                continue
            ha.post("/api/alarmo/automations", {
                "name": name, "type": "action", "enabled": bool(a.enable),
                "triggers": [{"event": event, "area": area}],
                "actions": [{"service": service, "entity_id": entity}]})
            created.append(name)
            time.sleep(1.1)
        return {"created": created, "enabled": bool(a.enable), "actions": await ha.ws_call("alarmo/automations")}
    raise SystemExit(f"unknown actions subcommand {sub}")


async def cmd_users(ha, a):
    sub = a.rest[0] if a.rest else "list"
    users = await ha.ws_call("alarmo/users")
    if sub == "list":
        return {k: {kk: vv for kk, vv in v.items() if kk != "code"} for k, v in users.items()}
    if sub == "add":
        if not sys.stdin.isatty():
            raise SystemExit("users add must be run in an interactive terminal (the code is typed, never passed in)")
        code = getpass.getpass("Code for the new user: ")
        if code != getpass.getpass("Repeat code: "):
            raise SystemExit("codes differ")
        ha.post("/api/alarmo/users", {"name": a.rest[1], "code": code, "enabled": True, "can_arm": True,
                                      "can_disarm": True, "is_override_code": False})
        return {"created": a.rest[1]}
    if sub == "update":
        changes = json.loads(a.rest[2])
        if "code" in changes:
            raise SystemExit("change codes in the Alarmo panel (Codes tab), not here")
        ha.post("/api/alarmo/users", {"user_id": a.rest[1], **changes})
        return (await ha.ws_call("alarmo/users")).get(a.rest[1], {})
    if sub == "remove":
        ha.post("/api/alarmo/users", {"user_id": a.rest[1], "remove": True})
        return {"removed": a.rest[1]}
    raise SystemExit(f"unknown users subcommand {sub}")


async def cmd_arm(ha, a, disarm=False):
    panels, _ = await _panels(ha)
    entity = a.entity or (panels[0]["entity_id"] if len(panels) == 1 else None)
    if not entity:
        raise SystemExit(f"several panels, pass --entity: {[p['entity_id'] for p in panels]}")
    code = os.environ.get(a.code_env, "") if a.code_env else ""
    data = {"entity_id": entity, "code": code}
    if not disarm:
        data |= {"mode": MODE_ALIASES.get(a.rest[0], a.rest[0]), "force": a.force, "skip_delay": a.skip_delay}
    await ha.ws_call("call_service", domain="alarmo", service="disarm" if disarm else "arm", service_data=data)
    await asyncio.sleep(1.5)
    st = (await ha.ws_call("get_states"))
    st = next(s for s in st if s["entity_id"] == entity)
    return {"entity_id": entity, "state": st["state"], "open_sensors": st["attributes"].get("open_sensors")}


async def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("command", choices=["status", "config", "area", "sensors", "actions", "users", "arm", "disarm"])
    p.add_argument("rest", nargs="*")
    p.add_argument("--url", default=os.environ.get("HA_URL"))
    p.add_argument("--token-env", default="HA_TOKEN")
    p.add_argument("--set")
    p.add_argument("--type", choices=list(TYPE_DEFAULTS))
    p.add_argument("--modes")
    p.add_argument("--area")
    p.add_argument("--entity")
    p.add_argument("--enable", action="store_true")
    p.add_argument("--code-env")
    p.add_argument("--force", action="store_true")
    p.add_argument("--skip-delay", action="store_true")
    a = p.parse_args()
    token = os.environ.get(a.token_env)
    if not a.url or not token:
        raise SystemExit(f"Set HA_URL (or --url) and {a.token_env}.")
    async with HA(a.url, token) as ha:
        if a.command == "status":
            res = await cmd_status(ha, a)
        elif a.command == "config":
            if a.set:
                ha.post("/api/alarmo/config", json.loads(a.set))
            res = await ha.ws_call("alarmo/config")
        elif a.command == "area":
            area = await _default_area(ha, a.rest[0] if a.rest else a.area)
            if a.set:
                changes = json.loads(a.set)
                cur = (await _areas(ha))[area]
                modes = cur["modes"]
                for m, v in (changes.pop("modes", {}) or {}).items():
                    m = MODE_ALIASES.get(m, m)
                    modes[m] = {**modes.get(m, {"enabled": False, "exit_time": 0, "entry_time": 0, "trigger_time": 0}), **v}
                ha.post("/api/alarmo/area", {"area_id": area, "name": changes.get("name", cur["name"]), "modes": modes})
            res = (await _areas(ha))[area]
        elif a.command == "sensors":
            res = await cmd_sensors(ha, a)
        elif a.command == "actions":
            res = await cmd_actions(ha, a)
        elif a.command == "users":
            res = await cmd_users(ha, a)
        elif a.command == "arm":
            res = await cmd_arm(ha, a)
        else:
            res = await cmd_arm(ha, a, disarm=True)
    json.dump(res, sys.stdout, indent=1, ensure_ascii=False)
    print()


if __name__ == "__main__":
    asyncio.run(main())
