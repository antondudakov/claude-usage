# claude-usage

One line of Claude usage for a status bar:

```
✻ $90/$1.4k ▰▱▱▱▱▱▱▱▱▱ 6% · Oct ▰▰▱▱▱▱▱▱▱▱ 18% · $16/d → +$858
```

The first bar is credits spent of the monthly limit, the second how much of the
month has gone; spend ahead of the month is spending too fast. `$16/d` is the
spend per day so far, and `→ +$858` what is left of the limit at month's end if
that pace holds; `→ -$300` means the limit runs out before the reset on the 1st.

When usage credits are off it shows the plan limits instead: `✻ 5h ▱▱▱▱▱▱▱▱▱▱ 3% · 7d ▱▱▱▱▱▱▱▱▱▱ 0%`.

It reads the login Claude Code already keeps (macOS Keychain, or
`~/.claude/.credentials.json` on Linux) and asks the same endpoint `/usage`
does. It never refreshes that login: if Claude Code has not run for a while it
says `login expired, run claude` until you start `claude` once.

The usage endpoint answers HTTP 429 when polled often, and iTerm2 asks from
every tab, so the answer is cached in `~/.cache/claude-usage.json` and fetched
at most once per 10 minutes. After a 429 it waits as long as the server's
`Retry-After` asks (up to an hour, as Claude Code does). On an error it keeps
showing the last answer.

## iTerm2 status bar (macOS)

```sh
ln -s "$PWD/claude_usage.py" ~/.local/bin/claude-usage
mkdir -p ~/Library/Application\ Support/iTerm2/Scripts/AutoLaunch
cp iterm2_claude_usage.py ~/Library/Application\ Support/iTerm2/Scripts/AutoLaunch/
```

1. iTerm2 → Settings → General → Magic → **Enable Python API**.
2. Scripts → AutoLaunch → **iterm2_claude_usage.py** (first run downloads
   iTerm2's Python runtime; after that it starts with iTerm2).
3. Settings → Profiles → Session → **Status bar enabled** → Configure Status
   Bar → drag **Claude usage** into the bar.

It refreshes every 15 minutes (`update_cadence` in the iTerm2 script).

## Anywhere else

`claude-usage` just prints the line, so tmux works too:
`set -g status-right '#(claude-usage)'` with `status-interval 900`.

Check: `python3 test_claude_usage.py`.
