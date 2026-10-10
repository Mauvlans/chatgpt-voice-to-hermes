# ChatGPT Voice — Always-On Linux Host

Run ChatGPT Desktop for Linux headlessly under `systemd --user` so the machine
stays reachable as a local Codex host from ChatGPT Voice on your phone, with
**Remote / Allow connections** automatically re-enabled after every app restart.

Verified against ChatGPT Desktop `26.825.51511` (Electron/Chrome 155) on
Ubuntu 26.04.

## Architecture

```text
ChatGPT mobile voice UI
        |  authenticated outbound ChatGPT Remote connection
        v
ChatGPT Desktop (headless, Xvfb :95, systemd --user)
        |  selected local Codex thread
        v
bundled `codex app-server`
        +--> filesystem / shell, subject to the thread permission profile
        +--> plugins, skills, MCP servers, connectors
```

Voice is not a separate daemon. It attaches to an existing Codex task and
inherits that task's permissions. No inbound port is opened; no router
port-forward is required.

## What this repo contains

| Path | Purpose |
|---|---|
| `systemd/chatgpt-display.service` | Xvfb `:95`, `-nolisten tcp` |
| `systemd/chatgpt-remote.service` | ChatGPT Desktop, loopback CDP on 9231 |
| `systemd/chatgpt-remote-enable.service` | oneshot: flips *Allow connections* back on |
| `bin/chatgpt-remote-enable.py` | CDP helper driving that toggle |
| `docs/SECURITY.md` | Threat model — **read before deploying** |

## Prerequisites

* ChatGPT Desktop installed and **already signed in interactively** on this host.
  This repo does not and cannot authenticate you.
* `xvfb`, `xdg-utils`, `x11-utils`, `python3-venv`.
* `systemd --user`, and linger if the host must stay up with nobody logged in.

```bash
sudo apt install -y xvfb xdg-utils x11-utils python3-venv
```

## Install

```bash
# 1. venv for the helper (PEP 668: do not use pip --user on 24.04+)
python3 -m venv ~/.local/share/chatgpt-remote/venv
~/.local/share/chatgpt-remote/venv/bin/pip install websocket-client

# 2. helper
install -D -m 700 bin/chatgpt-remote-enable.py ~/.local/bin/chatgpt-remote-enable.py
sed -i "1s|.*|#!$HOME/.local/share/chatgpt-remote/venv/bin/python|" \
    ~/.local/bin/chatgpt-remote-enable.py

# 3. units
mkdir -p ~/.config/systemd/user
cp systemd/*.service ~/.config/systemd/user/
sed -i "s|__HOME__|$HOME|g" ~/.config/systemd/user/chatgpt-remote-enable.service

# 4. verify the binary path matches ExecStart
command -v chatgpt

# 5. enable
systemctl --user daemon-reload
systemctl --user enable --now chatgpt-display.service chatgpt-remote.service
systemctl --user enable chatgpt-remote-enable.service
loginctl enable-linger "$USER"   # persistence change — understand it first
```

Stop any desktop-launched ChatGPT instance first; two instances fight over the
same `~/.config/Codex` profile.

## One-time interactive setup

1. Settings → Connections → enable **Allow connections**.
2. Pair your phone with the on-screen flow. Never copy pairing state between machines.
3. Enable **Keep this PC awake**.
4. Open or create a local Codex project.
5. Start Voice from that task; confirm the spoken request lands in that thread.

## Verification

```bash
systemctl --user is-active  chatgpt-display.service chatgpt-remote.service
systemctl --user is-enabled chatgpt-display.service chatgpt-remote.service
ss -ltn | grep 9231                      # must be 127.0.0.1 only
loginctl show-user "$USER" -p Linger
journalctl --user -u chatgpt-remote-enable.service -n 5
```

Crash-recovery test:

```bash
systemctl --user kill -s SIGKILL chatgpt-remote.service
sleep 45
systemctl --user is-active chatgpt-remote.service
journalctl --user -u chatgpt-remote-enable.service -n 3   # "ChatGPT Remote enabled"
```

## Design notes (why it looks like this)

* **The re-enable helper is a separate oneshot unit, not `ExecStartPost=`.**
  As `ExecStartPost` on a `Type=simple` unit, a non-zero exit kills the main
  process; combined with `Restart=always` that is an infinite crash loop every
  time ChatGPT changes the Connections markup.
* **`Requires=`/`After=` belong in `[Unit]`.** In `[Install]` systemd ignores
  them and the services start unordered.
* **`StartLimitIntervalSec`/`StartLimitBurst` belong in `[Unit]`** too — systemd
  logs `Unknown key ... in section [Service], ignoring` otherwise. Keep rate
  limiting on; do not set the interval to 0.
* **`ExecStartPre=/bin/rm -f /tmp/.X95-lock`** — a SIGKILLed Xvfb leaves a stale
  lock that blocks every restart.
* The helper re-fires `xdg-open codex://settings/connections` every 15s rather
  than once, because the settings page often does not exist on first attempt.

## Fragility

The helper matches `button[role="switch"][aria-label="Allow connections"]`.
That is UI-version-sensitive. If a ChatGPT update renames the control, the
oneshot fails loudly in the journal and Remote simply stays off — it will not
take the service down with it. Update the selector and re-run the unit.

## License

MIT
