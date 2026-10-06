import datetime
import json
import pathlib
import tempfile
import time
import urllib.error

import claude_usage
from claude_usage import line

today = datetime.date(2026, 10, 6)


def credits(used):
    return {"extra_usage": {"is_enabled": True, "used_credits": used, "monthly_limit": 136600,
                            "currency": "USD", "decimal_places": 2}}


cases = {
    9007: "✻ ▰▱▱▱▱▱▱▱▱▱ 6% · $90.07 / $1,366.00 · resets Nov 1",
    86058: "✻ ▰▰▰▰▰▰▱▱▱▱ 63% · $860.58 / $1,366.00 · resets Nov 1",
    125672: "✻ ▰▰▰▰▰▰▰▰▰▱ 92% · $1,256.72 / $1,366.00 · resets Nov 1",
    150000: "✻ ▰▰▰▰▰▰▰▰▰▰ 109% · $1,500.00 / $1,366.00 · resets Nov 1",
}
for used, expected in cases.items():
    assert line(credits(used), today) == expected, line(credits(used), today)

december = datetime.date(2026, 12, 31)
assert line(credits(9007), december).endswith("resets Jan 1"), line(credits(9007), december)

plan = {"five_hour": {"utilization": 2.0}, "seven_day": {"utilization": 41.6},
        "extra_usage": {"is_enabled": False}}
assert line(plan, today) == "✻ 5h ▱▱▱▱▱▱▱▱▱▱ 2% · 7d ▰▰▰▰▱▱▱▱▱▱ 42%", line(plan, today)

# One fetch per fresh window, the last answer kept through 429s for as long as
# Retry-After asks (10 min to 1 hour), 401 always shown.
claude_usage.CACHE = pathlib.Path(tempfile.mkdtemp()) / "claude-usage.json"
answers = ["✻ first"]


def fetch():
    answer = answers.pop(0)
    if isinstance(answer, tuple):
        raise urllib.error.HTTPError("", answer[0], "", answer[1], None)
    return answer


def ask_after(answer):
    """Expire the cache, answer once with `answer`, return the status and the wait it set."""
    cached = json.loads(claude_usage.CACHE.read_text())
    claude_usage.CACHE.write_text(json.dumps({**cached, "next": 0}))
    answers.append(answer)
    text = claude_usage.status()
    assert not answers
    return text, round((json.loads(claude_usage.CACHE.read_text())["next"] - time.time()) / 60)


claude_usage.fetch = fetch
assert claude_usage.status() == "✻ first"
assert claude_usage.status() == "✻ first" and not answers  # fresh: no second fetch
assert ask_after((429, {"Retry-After": "1800"})) == ("✻ first", 30)
assert ask_after((429, {})) == ("✻ first", 10)
assert ask_after((429, {"Retry-After": "86400"})) == ("✻ first", 60)
assert ask_after((401, {})) == ("✻ login expired, run claude", 10)

print("ok")
