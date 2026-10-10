#!__VENV_PYTHON__
"""Re-enable ChatGPT Remote 'Allow connections' after a desktop-app restart.

Talks only to a loopback CDP endpoint. Contains no account secrets.
Exits 0 on success, 1 on failure. Run as a separate oneshot unit so a
failure here never crash-loops the ChatGPT service.
"""
import json
import subprocess
import sys
import time
import urllib.request

import websocket

CDP_LIST = "http://127.0.0.1:9231/json/list"
CDP_ORIGIN = "http://localhost:9231"
DEADLINE_SECONDS = 90


def pages():
    with urllib.request.urlopen(CDP_LIST, timeout=2) as response:
        return json.load(response)


def evaluate(page, expression):
    ws = websocket.create_connection(
        page["webSocketDebuggerUrl"], origin=CDP_ORIGIN, timeout=5
    )
    try:
        ws.send(json.dumps({
            "id": 1,
            "method": "Runtime.evaluate",
            "params": {"expression": expression, "returnByValue": True},
        }))
        while True:
            message = json.loads(ws.recv())
            if message.get("id") == 1:
                result = message.get("result", {}).get("result", {})
                if result.get("subtype") == "error":
                    raise RuntimeError(result.get("description", "CDP evaluation failed"))
                return result.get("value")
    finally:
        ws.close()


READ_STATE = """(() => {
  const sel = 'button[role="switch"][aria-label="Allow connections"]';
  const t = document.querySelector(sel);
  if (!t) return null;
  return {enabled: t.getAttribute('aria-checked') === 'true'};
})()"""

ENABLE = """(() => {
  const sel = 'button[role="switch"][aria-label="Allow connections"]';
  const t = document.querySelector(sel);
  if (!t) return false;
  if (t.getAttribute('aria-checked') !== 'true') t.click();
  return true;
})()"""


def open_connections():
    subprocess.run(
        ["xdg-open", "codex://settings/connections"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        timeout=10, check=False,
    )


def main():
    deadline = time.monotonic() + DEADLINE_SECONDS

    while time.monotonic() < deadline:
        try:
            if any(p.get("type") == "page" for p in pages()):
                break
        except Exception:
            pass
        time.sleep(1)
    else:
        print("ChatGPT debugging endpoint did not become ready", file=sys.stderr)
        return 1

    last_error = "toggle unavailable"
    last_open = 0.0
    while time.monotonic() < deadline:
        # Re-fire the deep link periodically: the settings page may not have
        # existed yet on the first attempt.
        if time.monotonic() - last_open > 15:
            open_connections()
            last_open = time.monotonic()
            time.sleep(2)
        try:
            for page in pages():
                if page.get("type") != "page":
                    continue
                try:
                    state = evaluate(page, READ_STATE)
                except Exception as error:
                    last_error = "%s: %s" % (page.get("url", "?")[:60], error)
                    continue
                if state is None:
                    continue
                if not state["enabled"]:
                    evaluate(page, ENABLE)
                    time.sleep(2)
                    state = evaluate(page, READ_STATE)
                if state and state["enabled"]:
                    print("ChatGPT Remote enabled")
                    return 0
        except Exception as error:
            last_error = str(error)
        time.sleep(1)

    print("ChatGPT Remote could not be enabled: " + last_error, file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
