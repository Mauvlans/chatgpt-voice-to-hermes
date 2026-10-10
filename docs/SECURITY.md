# Security model

## The debugging port is the whole threat model

`--remote-debugging-port=9231` exposes a Chrome DevTools Protocol endpoint for
a **signed-in ChatGPT application** with access to a local Codex host. Loopback
binding is a reduction of exposure, not a security boundary:

* Any local process running as this user can drive the app — read conversations,
  change settings, start Codex tasks with that thread's permissions.
* Anything that can make the browser on this machine issue requests to
  `127.0.0.1:9231` is in scope. `--remote-allow-origins` is restricted to
  `http://localhost:9231` to blunt, not eliminate, this.

Do not deploy this on a multi-user host, and never bind the port to a LAN or
public address.

## Codex permissions

Voice does **not** require unrestricted filesystem access. `danger-full-access`
with `approval_policy = "never"` is a separate, independent decision — do not
adopt it because a Voice guide used it. A sane starting `~/.codex/config.toml`:

```toml
approval_policy = "on-request"
sandbox_mode    = "workspace-write"

[projects."/path/to/an/approved/project"]
trust_level = "trusted"
```

Add only the project roots, plugins, skills and MCP servers actually needed.

## Other rules

* `Xvfb` runs with `-nolisten tcp`. Keep it that way.
* Never copy `~/.config/Codex`, Chromium/Electron profiles, cookies, tokens or
  device-pairing state between users or machines. Authenticate on each host.
* Never put OpenAI or third-party tokens in unit files or docs.
* Back up `~/.config/Codex` before first headless start; a profile used by two
  concurrent instances can be corrupted.
* Review any remote-triggered action that can send messages, spend money,
  unlock doors, or change infrastructure. Voice inherits the task's permissions
  — the always-on host does not need broad access merely to support Voice.
