# HA Alarmo (agent plugin)

Agent skills for [Alarmo](https://github.com/nielsfaber/alarmo), the local alarm system for Home Assistant. They manage
it through its own websocket and REST API, so there's no clicking through the panel and no `.storage` edits.

## Skills

| Skill | What it does |
|---|---|
| `status` | Panel state, open sensors, readiness to arm, modes, sensors, enabled outputs, users (no codes) |
| `setup` | Install via HACS, area name, arm modes (exit/entry/trigger times), global code settings |
| `sensors` | Find candidate binary sensors, add with type-appropriate defaults, tune, remove |
| `actions` | Sirens on trigger / off at disarm (created disabled by default), notifications, enable/disable |
| `users` | List and manage users; codes are typed by the user in their own terminal, never by the agent |
| `arm` | Arm/disarm only on explicit request, plus a supervised test procedure with sirens off |

## Helper script

`scripts/alarmo.py` is a self-contained `uv` script. It needs `HA_URL` and `HA_TOKEN` (an admin long-lived token).

```bash
uv run scripts/alarmo.py status
uv run scripts/alarmo.py sensors candidates
uv run scripts/alarmo.py sensors add binary_sensor.front_door_contact
uv run scripts/alarmo.py actions sirens group.sirens          # disabled until you pass --enable
uv run scripts/alarmo.py area --set '{"modes": {"away": {"trigger_time": 300}}}'
```

Tested against Alarmo 1.10.19 on Home Assistant 2026.11: status, candidates, sensor update, action enable/disable,
area update, disarm. `arm` follows the same service call as `disarm` (`alarmo.arm`) but has not been run against a
live system by the author.

## Installation

```bash
claude plugins install ha-alarmo@danielrosehill
```

## License

MIT
