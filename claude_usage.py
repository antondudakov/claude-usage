#!/usr/bin/env python3
"""Print one line of Claude usage for a status bar: credits spent of the monthly
limit, or the 5-hour/7-day plan limits when usage credits are off."""
import datetime
import fcntl
import json
import pathlib
import subprocess
import sys
import time
import urllib.error
import urllib.request

# iTerm2 asks from every tab and the endpoint answers 429 when polled often, so
# all callers share one answer and the time it may next be asked.
CACHE = pathlib.Path.home() / ".cache/claude-usage.json"
FRESH_SECONDS = 10 * 60
MAX_WAIT_SECONDS = 60 * 60  # Claude Code caps the endpoint's Retry-After here too


def token():
    # Reads the login Claude Code keeps; never refreshes it, since refresh
    # tokens rotate and refreshing here would log Claude Code out.
    if sys.platform == "darwin":
        raw = subprocess.run(
            ["security", "find-generic-password", "-s", "Claude Code-credentials", "-w"],
            capture_output=True, text=True, check=True,
        ).stdout
    else:
        raw = (pathlib.Path.home() / ".claude/.credentials.json").read_text()
    return json.loads(raw)["claudeAiOauth"]["accessToken"]


def meter(percent):
    # ▰/▱ share a width; spaces would not in the status bar's proportional font.
    filled = int(min(percent, 100) / 10 + 0.5)
    return f"{'▰' * filled}{'▱' * (10 - filled)} {percent:.0f}%"


def line(usage, today):
    credits = usage.get("extra_usage") or {}
    if not credits.get("is_enabled"):
        five = (usage.get("five_hour") or {}).get("utilization") or 0
        week = (usage.get("seven_day") or {}).get("utilization") or 0
        return f"✻ 5h {meter(five)} · 7d {meter(week)}"
    # Amounts are minor units of the currency (cents for USD).
    scale = 10 ** (credits.get("decimal_places") or 2)
    currency = credits.get("currency") or "USD"
    sign = "$" if currency == "USD" else currency + " "
    used = credits["used_credits"] / scale
    out = f"✻ {sign}{used:,.2f}"
    if credits.get("monthly_limit"):
        limit = credits["monthly_limit"] / scale
        percent = int(used / limit * 100)
        out = f"✻ {meter(percent)} · {sign}{used:,.2f} / {sign}{limit:,.2f}"
    reset = (today.replace(day=1) + datetime.timedelta(days=32)).replace(day=1)
    return out + f" · resets {reset:%b} {reset.day}"


def fetch():
    request = urllib.request.Request(
        "https://api.anthropic.com/api/oauth/usage",
        headers={"Authorization": f"Bearer {token()}", "anthropic-beta": "oauth-2025-04-20"},
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return line(json.load(response), datetime.date.today())


def status():
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE.with_suffix(".lock"), "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)  # tabs refreshing together wait for one request
        try:
            cached = json.loads(CACHE.read_text())
        except (OSError, ValueError):
            cached = {}
        if time.time() < cached.get("next", 0):
            return cached["text"]
        wait = FRESH_SECONDS
        try:
            text = fetch()
        except urllib.error.HTTPError as e:
            text = "✻ login expired, run claude" if e.code == 401 else cached.get("text") or f"✻ HTTP {e.code}"
            if e.code == 429:
                after = e.headers.get("Retry-After", "")
                wait = min(max(int(after) if after.isdigit() else 0, FRESH_SECONDS), MAX_WAIT_SECONDS)
        except OSError:
            text = cached.get("text") or "✻ offline"
        # A failure keeps the last answer and still waits before asking again.
        CACHE.write_text(json.dumps({"text": text, "next": time.time() + wait}))
        return text


if __name__ == "__main__":
    print(status())
