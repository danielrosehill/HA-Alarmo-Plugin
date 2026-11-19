---
name: actions
description: Manage Alarmo actions on Home Assistant - sirens on trigger and off on disarm, notifications, enable/disable, without arming.
---

# Alarmo actions (sirens, notifications)

Alarmo "automations" fire on alarm events: `trigger`, `disarm`, `arm`, `leave` (exit delay started), `entry`
(entry delay started), `failed_to_arm`, `command_not_allowed`, `invalid_code_provided`, `no_code_provided`,
`trigger_time_expired`. Each has `type` `action` (call services) or `notification`.

```bash
alarmo.py actions list
alarmo.py actions sirens group.sirens            # creates "on at trigger" + "off at disarm", DISABLED
alarmo.py actions sirens group.sirens --enable   # same, enabled
alarmo.py actions enable <id>   |   alarmo.py actions disable <id>   |   alarmo.py actions remove <id>
alarmo.py actions add '{"name": "Notify phone on trigger", "type": "notification", "enabled": true, "triggers": [{"event": "trigger", "area": "<area_id>"}], "actions": [{"service": "notify.mobile_app_phone", "service_data": {"title": "Alarm", "message": "{{open_sensors}} triggered the alarm"}}]}'
```

`sirens` works with any entity `homeassistant.turn_on` accepts (a `siren.*`, a `switch.*` siren, or a group).
For `siren.*` entities with tones/volume, use `actions add` with `siren.turn_on` and `service_data`.

## Rules

- **Enabling a siren action is going live.** Do it only when the user says so. While the alarm stays disarmed
  nothing fires, but someone might arm it from a dashboard.
- Always pair "sirens on at trigger" with "sirens off at disarm". Also set a finite area `trigger_time`, so a
  trigger nobody is home to disarm stops by itself.
- Alarmo action ids are unix seconds, so two creates in the same second overwrite each other. The script waits 1.1 s;
  if you POST by hand, do the same.
- Test sirens separately from the alarm (turn the siren entity on and off yourself, after warning the household), not by
  triggering the alarm.

## Connection

`uv run ${CLAUDE_PLUGIN_ROOT}/scripts/alarmo.py ...` needs `HA_URL` and `HA_TOKEN` (an admin long-lived token).
Settings persist in `${CLAUDE_USER_DATA:-${XDG_DATA_HOME:-$HOME/.local/share}/claude-plugins}/ha-alarmo/config.json`
as `{"ha_url": "...", "token_env": "HA_TOKEN", "token_command": "<optional command that prints the token>"}`.
Read it first. If it is missing, ask for the URL and how to get the token, and write it. Never store the token.
