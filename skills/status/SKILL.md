---
name: status
description: Show Alarmo alarm status on Home Assistant - panel state, open sensors, modes, sensors, siren/notification actions, users - and readiness to arm.
---

# Alarmo status

```bash
uv run ${CLAUDE_PLUGIN_ROOT}/scripts/alarmo.py status
```

Returns `panels` (state, open_sensors, bypassed_sensors, changed_by, last_triggered), `config` (code requirements,
MQTT, master panel), `areas` (modes with exit/entry/trigger seconds), `sensors` (entity, current state, type, modes,
delays, always_on), `actions` (Alarmo automations: id, enabled, triggers, actions) and `users` (names and rights,
never codes).

Summarise for the user in plain words:

- **State**: disarmed, arming, armed_*, pending (entry delay), triggered.
- **Ready to arm?** Any sensor that is open (`on`) and in a mode's `modes` list blocks arming that mode, unless
  it has `allow_open` or auto-bypass.
- **Outputs**: which actions are enabled. "Sirens on at trigger" disabled means a triggered alarm is silent.
- **Codes**: no users means nobody needs a code (fine while staging, not for real use).
- **Gaps**: entry points without a sensor, `trigger_time` 0 (sounds until disarmed), and no notification action.

## Connection

`uv run ${CLAUDE_PLUGIN_ROOT}/scripts/alarmo.py ...` needs `HA_URL` and `HA_TOKEN` (an admin long-lived token).
Settings persist in `${CLAUDE_USER_DATA:-${XDG_DATA_HOME:-$HOME/.local/share}/claude-plugins}/ha-alarmo/config.json`
as `{"ha_url": "...", "token_env": "HA_TOKEN", "token_command": "<optional command that prints the token>"}`.
Read it first. If it is missing, ask for the URL and how to get the token, and write it. Never store the token.
