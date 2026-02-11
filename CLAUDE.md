# llll — LEGO lin la loop

An MCP server that gives AI agents the ability to run MicroPython programs on LEGO Mindstorms hubs via Pybricks.

## Project Structure

```
src/llll/
├── server.py       — MCP server (FastMCP-based)
├── cli.py          — Command-line interface (init, flash)
├── runner.py       — pybricksdev subprocess wrapper + log capture
├── logs.py         — Log file management
├── config.py       — llll.toml configuration management
├── discover.py     — Hub detection and device discovery (includes version detection)
├── firmware.py     — Firmware version checking and flashing
└── __init__.py     — Package initialization
logs/               — Captured run output (gitignored)
pyproject.toml      — Python package configuration
```

## MCP Tools

The server exposes six tools for AI agents:

1. **detect_hub** — Auto-detect hub type, name, battery, Pybricks version, and connected devices. Saves to `llll.toml`
2. **get_hub_info** — Read configured hub information from `llll.toml` (includes firmware version)
3. **run_program** — Compile, upload, and run a `.py` file on the hub via Bluetooth
4. **list_programs** — Find `.py` files in the workspace
5. **read_log** — Read output from a previous run
6. **list_run_logs** — List all available run logs

### Firmware Management

**Version Detection:** When `detect_hub` runs, it detects the Pybricks firmware version and includes it in the hub info. Agents can see this and advise users if an update is available.

**Flashing (CLI only, not a tool):** Firmware flashing is intentionally NOT exposed as an MCP tool because it's a destructive operation. Instead, agents should guide users to run `llll flash --check` or `llll flash` manually. This ensures users understand what's happening before modifying their hub's firmware.

## Installation & Setup

Users typically install llll globally and initialize workspaces:

```bash
# Install globally
pipx install llll

# Initialize MCP integration in a project
cd robot-project/
llll init

# Optionally detect hub hardware
llll init --detect
```

The `llll init` command creates:
- `.mcp.json` — MCP client configuration
- `llll.toml` — Hub hardware configuration (if `--detect` used)

The MCP server automatically creates a `logs/` directory when programs are run.

## Development

```bash
# Install in editable mode
pip install -e .

# Test the init command
mkdir test && cd test
llll init

# Run the MCP server directly
llll
```

## How It Works

The MCP server exposes tools that agents call autonomously:
1. Agent writes a `.py` file to the workspace
2. Agent calls `run_program(file="my_program.py")` — this compiles, uploads via BLE, runs on hub, captures output
3. Agent reads the returned output (print statements from the hub)
4. Agent iterates — fixes bugs, tunes behavior, runs again

## Writing Hub Programs

Programs run on a LEGO hub with Pybricks firmware. This is a **subset of MicroPython** — not full Python.

### Available modules
- `pybricks.hubs` — Hub classes (InventorHub, PrimeHub, TechnicHub, etc.)
- `pybricks.pupdevices` — Motors, ColorSensor, UltrasonicSensor, ForceSensor, etc.
- `pybricks.parameters` — Constants: Port, Direction, Stop, Color, Button, Side
- `pybricks.tools` — wait(), StopWatch, multitask(), run_task()
- `pybricks.robotics` — DriveBase for differential drive
- Standard: `umath`, `urandom`, `ustruct`, `ujson`, `usys`

### Key constraints
- **No filesystem** — can't read/write files on the hub
- **No networking** — no sockets, HTTP, or wifi
- **No REPL** — programs run as batch scripts
- **No `time` module** — use `pybricks.tools.wait()` and `StopWatch`
- **No `os` or `sys`** — use `usys` for stdin/stdout
- **RAM-limited** — keep programs reasonably small
- **print() is your telemetry** — all observability comes through print() statements

### Async support
```python
from pybricks.tools import multitask, run_task, wait

async def task_a():
    ...

async def task_b():
    ...

async def main():
    await multitask(task_a(), task_b())

run_task(main())
```

## Hardware Notes

- Hub must have **Pybricks firmware** flashed (one-time setup via `pybricksdev flash`)
- Connection is via **Bluetooth LE** — hub must be in pairing mode (press button until it flashes)
- Programs **cannot be stopped from CLI** — press the physical hub button to stop
- On macOS, use `hub_name` parameter to target a specific hub (BLE address doesn't work)
