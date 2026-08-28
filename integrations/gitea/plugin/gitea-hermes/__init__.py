"""Native Gitea integration for Hermes Agent."""
from __future__ import annotations

from .schemas import SCHEMAS, READ_TOOLS, WRITE_TOOLS
from .tools import HANDLERS


def register(ctx):
    """Register tools only; deliberately performs no network or filesystem mutation."""
    for name in sorted(SCHEMAS):
        ctx.register_tool(
            name=name,
            toolset="gitea_read" if name in READ_TOOLS else "gitea_write",
            schema=SCHEMAS[name],
            handler=HANDLERS[name],
        )
