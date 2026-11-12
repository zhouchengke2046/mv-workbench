"""Best-effort UTF-8 console setup for Windows cp1252 pipes."""
import sys


def setup():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
