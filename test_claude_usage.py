import datetime
import json
import pathlib
import tempfile
import time
import urllib.error

import claude_usage
from claude_usage import line

today = datetime.datetime(2026, 10, 6, 12)  # 5.5 days into October


def credits(used):
    return {"extra_usage": {"is_enabled": True, "used_credits": used, "monthly_limit": 136600,
                            "currency": "USD", "decimal_places": 2}}


cases = {
    0: "✻ $0/$1.4k ▱▱▱▱▱▱▱▱▱▱ 0% · Oct ▰▰▱▱▱▱▱▱▱▱ 18% · $0/d → +$1.4k",
    9007: "✻ $90/$1.4k ▰▱▱▱▱▱▱▱▱▱ 6% · Oct ▰▰▱▱▱▱▱▱▱▱ 18% · $16/d → +$858",
    86058: "✻ $861/$1.4k ▰▰▰▰▰▰▱▱▱▱ 63% · Oct ▰▰▱▱▱▱▱▱▱▱ 18% · $156/d → -$3.5k",
    125672: "✻ $1.3k/$1.4k ▰▰▰▰▰▰▰▰▰▱ 92% · Oct ▰▰▱▱▱▱▱▱▱▱ 18% · $228/d → -$5.7k",
    150000: "✻ $1.5k/$1.4k ▰▰▰▰▰▰▰▰▰▰ 109% · Oct ▰▰▱▱▱▱▱▱▱▱ 18% · $273/d → -$7.1k",
}
for used, expected in cases.items():
    assert line(credits(used), today) == expected, line(credits(used), today)

# December has 31 days too: the month's bar is nearly full on the last evening.
december = datetime.datetime(2026, 12, 31, 23)
assert "Dec ▰▰▰▰▰▰▰▰▰▰ 100% · $3/d" in line(credits(9007), december), line(credits(9007), december)

# A minute into the month counts as an hour, not as a whole day's spend.
first_minute = datetime.datetime(2026, 10, 1, 0, 1)
assert line(credits(500), first_minute).endswith("$120/d → -$2.4k"), line(credits(500), first_minute)

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
