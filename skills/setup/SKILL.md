---
name: setup
description: Install and set up Alarmo on Home Assistant - HACS install, area name, arm modes with exit/entry/trigger times, global code settings.
---

# Set up Alarmo

Alarmo (`nielsfaber/alarmo`, HACS integration plus a `custom:alarmo-card`) is a fully local alarm system. All its
config lives in its own storage. There is no YAML, so use the script, never `.storage` edits.

1. **Installed?** Run `alarmo.py status`. If it fails with an unknown command, install Alarmo from HACS (default
   repository, category integration), restart core, then add the integration (*Settings → Devices & services → Add
   → Alarmo*, or config flow handler `alarmo`). Also install the **Alarmo Card** (HACS frontend) for dashboards.
2. **Area and modes.** One area is typical. Name it and enable the modes the user wants:
   ```bash
   alarmo.py area --set '{"name": "Home", "modes": {"away": {"enabled": true, "exit_time": 60, "entry_time": 30, "trigger_time": 300}, "home": {"enabled": true, "exit_time": 0, "entry_time": 30, "trigger_time": 300}, "night": {"enabled": true, "exit_time": 0, "entry_time": 30, "trigger_time": 300}}}'
   ```
   Mode keys: away, home, night, vacation, custom. `exit_time` is the time to leave after arming, `entry_time` the
   time to disarm after an entry sensor opens, and `trigger_time` how long the alarm stays triggered (0 = until
   disarmed; prefer a finite value such as 300 s). Renaming the area renames the panel entity
   (`alarm_control_panel.<area>`): check dashboards and automations for the old id first.
3. **Global config**: `alarmo.py config --set '{"code_arm_required": false, "code_disarm_required": true, "disarm_after_trigger": false}'`.
   Turn on `code_disarm_required` only after a user with a code exists (`users` skill), or nobody can disarm.
4. Continue with the `sensors` skill, then `actions` (sirens, notifications), then `users`.

Staged, unarmed setup: everything above can be done with the panel left disarmed. Leave siren actions disabled
until the user says the system is going live.

## Connection

`uv run ${CLAUDE_PLUGIN_ROOT}/scripts/alarmo.py ...` needs `HA_URL` and `HA_TOKEN` (an admin long-lived token).
Settings persist in `${CLAUDE_USER_DATA:-${XDG_DATA_HOME:-$HOME/.local/share}/claude-plugins}/ha-alarmo/config.json`
as `{"ha_url": "...", "token_env": "HA_TOKEN", "token_command": "<optional command that prints the token>"}`.
Read it first. If it is missing, ask for the URL and how to get the token, and write it. Never store the token.
