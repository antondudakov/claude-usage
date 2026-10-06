import datetime

from claude_usage import line

today = datetime.date(2026, 10, 6)


def credits(used):
    return {"extra_usage": {"is_enabled": True, "used_credits": used, "monthly_limit": 136600,
                            "currency": "USD", "decimal_places": 2}}


cases = {
    9007: "✻ ▁ 6% · $90.07 / $1,366.00 · resets Nov 1",
    86058: "✻ ▅ 63% · $860.58 / $1,366.00 · resets Nov 1",
    125672: "✻ ▇ 92% · $1,256.72 / $1,366.00 · resets Nov 1",
    150000: "✻ █ 109% · $1,500.00 / $1,366.00 · resets Nov 1",
}
for used, expected in cases.items():
    assert line(credits(used), today) == expected, line(credits(used), today)

december = datetime.date(2026, 12, 31)
assert line(credits(9007), december).endswith("resets Jan 1"), line(credits(9007), december)

plan = {"five_hour": {"utilization": 2.0}, "seven_day": {"utilization": 41.6},
        "extra_usage": {"is_enabled": False}}
assert line(plan, today) == "✻ 5h ▁ 2% · 7d ▄ 42%", line(plan, today)

print("ok")
