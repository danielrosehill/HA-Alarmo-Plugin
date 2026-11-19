---
name: sensors
description: Add, tune or remove Alarmo sensors (door, window, motion, tamper, smoke/CO) on Home Assistant; find candidate binary sensors.
---

# Alarmo sensors

```bash
alarmo.py sensors candidates        # binary sensors not yet in Alarmo, with a suggested type from device_class
alarmo.py sensors list
alarmo.py sensors add binary_sensor.front_door_contact                    # type + defaults from device_class
alarmo.py sensors add binary_sensor.hall_motion --modes away,night
alarmo.py sensors add binary_sensor.kitchen_smoke --type environmental    # always on, ignores arm state
alarmo.py sensors update binary_sensor.front_door_contact '{"use_entry_delay": true, "entry_delay": 45}'
alarmo.py sensors remove binary_sensor.old_sensor
```

(`alarmo.py` = `uv run ${CLAUDE_PLUGIN_ROOT}/scripts/alarmo.py`.)

## Choosing the type and options

| Type | Typical source | Default modes | Delays | Notes |
|---|---|---|---|---|
| door | entry doors, garage | away, home, night, vacation | entry + exit | the door you come in through needs entry delay |
| window | windows | away, home, night, vacation | none | trips at once |
| motion | PIR / occupancy | away, vacation | entry + exit | not in home/night: you'd trip it yourself |
| tamper | sensor tamper switches | all | none | |
| environmental | smoke, CO, gas, leak | none (always_on) | none | triggers even when disarmed; only add if Alarmo should sound for it |
| other | anything else | away, vacation | entry + exit | |

Other options: `arm_on_close` (arm as soon as this door closes after arming), `allow_open` (may be open
when arming), `trigger_unavailable` (trip when the sensor goes unavailable; good for wired/mains sensors, noisy for
battery Zigbee), `auto_bypass` + `auto_bypass_modes` (skip an open sensor instead of refusing to arm),
`entry_delay` (per-sensor override in seconds).

## Care

- **Presence or occupancy sensors that track people** (e.g. a baby or pet monitor) are suggested as motion. Ask
  before adding them; they are rarely intruder detectors.
- **Environmental sensors with always_on** will sound the sirens (once siren actions are enabled) for smoke/CO even
  when disarmed. Confirm the user wants that, and that a separate fire automation won't double up.
- After changes, run `status` and check the sensor's current state, since an open sensor blocks arming.

## Connection

`uv run ${CLAUDE_PLUGIN_ROOT}/scripts/alarmo.py ...` needs `HA_URL` and `HA_TOKEN` (an admin long-lived token).
Settings persist in `${CLAUDE_USER_DATA:-${XDG_DATA_HOME:-$HOME/.local/share}/claude-plugins}/ha-alarmo/config.json`
as `{"ha_url": "...", "token_env": "HA_TOKEN", "token_command": "<optional command that prints the token>"}`.
Read it first. If it is missing, ask for the URL and how to get the token, and write it. Never store the token.
