#!/usr/bin/env python3
"""iTerm2 status bar component that shows claude-usage, refreshed every 15 minutes."""
import asyncio
import os
import sys

import iterm2

CLAUDE_USAGE = os.path.expanduser("~/.local/bin/claude-usage")


async def main(connection):
    component = iterm2.StatusBarComponent(
        short_description="Claude usage",
        detailed_description="Claude usage credits spent of the monthly limit",
        knobs=[],
        exemplar="✻ ▁ 6% · $90.07 / $1,366.00 · resets Nov 1",
        update_cadence=15 * 60,
        identifier="com.antondudakov.claude-usage",
    )

    @iterm2.StatusBarRPC
    async def usage(knobs):
        process = await asyncio.create_subprocess_exec(
            sys.executable, CLAUDE_USAGE, stdout=asyncio.subprocess.PIPE
        )
        out, _ = await process.communicate()
        return out.decode().strip() or "✻ ?"

    await component.async_register(connection, usage)


iterm2.run_forever(main)
