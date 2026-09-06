"""Kronos - a fund manager agent with a pluggable "vibe trading" strategy.

Kronos never sends a real order unless it is explicitly configured to
("LIVE_TRADING=true") and, on top of that, a human approves every live
order before it is submitted to the broker.
"""

__version__ = "0.1.0"
