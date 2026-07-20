"""
Tool pinning for rug-pull detection.

Fingerprints each tool (name + description + input schema) with a SHA-256 hash
and stores it. On a later scan, if a tool's fingerprint no longer matches its
stored pin, the tool definition changed after approval -- the signature of a
rug-pull attack (a server that ships clean, then silently mutates a tool).
"""

import hashlib
import json
from pathlib import Path

PIN_FILE = Path("scanner/pins.json")


def fingerprint(tool):
    blob = json.dumps({
        "name": tool.name,
        "description": tool.description,
        "schema": tool.inputSchema,
    }, sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()


def load_pins():
    if PIN_FILE.exists():
        return json.loads(PIN_FILE.read_text())
    return {}


def save_pins(pins):
    PIN_FILE.write_text(json.dumps(pins, indent=2))


def check_and_update(tool, pins):
    """Return status: 'new', 'unchanged', or 'CHANGED (possible rug pull)'."""
    fp = fingerprint(tool)
    key = tool.name
    if key not in pins:
        status = "new"
    elif pins[key] == fp:
        status = "unchanged"
    else:
        status = "CHANGED (possible rug pull)"
    pins[key] = fp
    return status