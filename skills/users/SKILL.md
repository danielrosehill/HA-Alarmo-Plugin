---
name: users
description: Manage Alarmo users and PIN codes on Home Assistant - list, rights, enable/disable, remove; codes are typed by the user, never the agent.
---

# Alarmo users and codes

```bash
alarmo.py users list                               # names, rights, area limits (codes are never shown)
alarmo.py users update <user_id> '{"can_disarm": true, "enabled": false}'
alarmo.py users remove <user_id>
```

**Codes are secrets. The agent never sees, chooses or types one.** To add a user, the user runs this in their own
terminal (in Claude Code: `! uv run <plugin>/scripts/alarmo.py users add "Name"`). It prompts for the code twice with
hidden input. Or they add it in the Alarmo panel (sidebar *Alarmo → Codes*). Changing a code works the same way.

Rights: `can_arm`, `can_disarm`, `is_override_code` (arms even with open sensors; give it sparingly),
`area_limit` (list of area ids). Link a user to an HA user (`user_id` of the person) to make `changed_by` meaningful.

After the first user exists, suggest `config --set '{"code_disarm_required": true}'` (`setup` skill), so the alarm
can't be disarmed from any dashboard without a code.

## Connection

`uv run ${CLAUDE_PLUGIN_ROOT}/scripts/alarmo.py ...` needs `HA_URL` and `HA_TOKEN` (an admin long-lived token).
Settings persist in `${CLAUDE_USER_DATA:-${XDG_DATA_HOME:-$HOME/.local/share}/claude-plugins}/ha-alarmo/config.json`
as `{"ha_url": "...", "token_env": "HA_TOKEN", "token_command": "<optional command that prints the token>"}`.
Read it first. If it is missing, ask for the URL and how to get the token, and write it. Never store the token.
