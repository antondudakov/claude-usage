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
# all callers share one answer for this long.
CACHE = pathlib.Path.home() / ".cache/claude-usage"
FRESH_SECONDS = 10 * 60


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
    return f"{'▁▂▃▄▅▆▇█'[round(min(percent, 100) / 100 * 7)]} {percent:.0f}%"


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
    with open(f"{CACHE}.lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)  # tabs refreshing together wait for one request
        cached = CACHE.read_text(encoding="utf-8") if CACHE.exists() else None
        if cached and time.time() - CACHE.stat().st_mtime < FRESH_SECONDS:
            return cached
        try:
            text = fetch()
        except urllib.error.HTTPError as e:
            text = "✻ login expired, run claude" if e.code == 401 else cached or f"✻ HTTP {e.code}"
        except OSError:
            text = cached or "✻ offline"
        # Rewriting a stale answer after a failure also waits FRESH_SECONDS before retrying.
        CACHE.write_text(text, encoding="utf-8")
        return text


if __name__ == "__main__":
    print(status())
