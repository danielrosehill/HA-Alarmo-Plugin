---
name: arm
description: Arm or disarm Alarmo on Home Assistant (away/home/night/vacation) safely, and run a supervised alarm test without sirens.
---

# Arm, disarm, test

```bash
alarmo.py disarm [--code-env ALARM_CODE]
alarmo.py arm away|home|night|vacation [--code-env ALARM_CODE] [--force] [--skip-delay]
```

Returns the panel state and any open sensors. With `--code-env`, the code is read from an environment variable
the **user** set (`export ALARM_CODE=...` in their own shell). Never ask the user to paste a code into chat.

## Rules

- **Arm only when the user explicitly asks, in this conversation, for a specific mode.** Arming makes sirens and
  notifications possible. A standing request like "set up the alarm" is not a request to arm.
- Before arming, run `status`: say which sensors are open, which actions are enabled (sirens yes/no), and the exit
  delay, then arm. `--force` arms despite open sensors (they are bypassed); say so.
- Disarming is always fine to do on request.

## Supervised test (no noise)

1. `status`: confirm the siren actions are **disabled** (or disable them with the `actions` skill; note to
   re-enable).
2. Tell the user what will happen, then `arm away` with the user at home, and wait for the exit delay
   (state `arming` → `armed_away`).
3. The user opens an armed door: state becomes `pending` (entry delay), then `triggered` if not disarmed.
4. `disarm`. Check `last_triggered` and the HA logbook for the panel. Re-enable siren actions only if they were
   on before.

## Connection

`uv run ${CLAUDE_PLUGIN_ROOT}/scripts/alarmo.py ...` needs `HA_URL` and `HA_TOKEN` (an admin long-lived token).
Settings persist in `${CLAUDE_USER_DATA:-${XDG_DATA_HOME:-$HOME/.local/share}/claude-plugins}/ha-alarmo/config.json`
as `{"ha_url": "...", "token_env": "HA_TOKEN", "token_command": "<optional command that prints the token>"}`.
Read it first. If it is missing, ask for the URL and how to get the token, and write it. Never store the token.
