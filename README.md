# llll — LEGO LIN LA LOOP

An MCP (Model Context Protocol) server that gives AI agents the ability to run MicroPython programs on LEGO Mindstorms hubs via [Pybricks](https://pybricks.com/).

## What is this?

This MCP server creates an agentic development loop for LEGO robotics:

1. An AI agent writes a MicroPython program for a LEGO hub
2. The agent uses `run_program()` to compile, upload via Bluetooth, and execute it on the physical hardware
3. The agent reads the output (from `print()` statements) and iterates

The agent can detect hardware, debug programs, tune behavior, and autonomously develop robot code through an observe-test-refine cycle.

## Features

- **Hardware Detection**: Auto-detect hub type, connected motors, sensors, and battery level
- **Wireless Execution**: Run programs on LEGO hubs via Bluetooth LE
- **Output Capture**: All `print()` statements and errors are captured and returned to the agent
- **Log Management**: Automatic logging of all runs with timestamps
- **MCP-Native**: Built with FastMCP for seamless integration with Claude and other MCP clients

## Prerequisites

- Python 3.10+
- A LEGO hub with [Pybricks firmware](https://pybricks.com/install/) installed (one-time setup)
- Bluetooth connectivity
- `pybricksdev` CLI tool (installed automatically)

**Supported Hubs:**
- LEGO SPIKE Prime Hub / SPIKE Essential Hub
- LEGO Mindstorms Robot Inventor Hub
- LEGO Technic Hub
- LEGO City Hub
- LEGO BOOST Move Hub

## Installation

### Using pipx (Recommended)

```bash
# Install globally with pipx
pipx install llll

# Initialize a new workspace
cd your-robot-project/
llll init

# Optionally detect your hub immediately
llll init --detect
```

### Using pip

```bash
pip install llll
```

### From Source

```bash
git clone https://github.com/mattprindible/llll.git
cd llll
pip install -e .
```

## Quick Start

1. **Install llll globally:**
   ```bash
   pipx install llll
   ```

2. **Initialize your robot project:**
   ```bash
   cd your-robot-project/
   llll init
   ```
   This creates `.mcp.json` for MCP client configuration.

3. **Optionally detect your hub:**
   ```bash
   llll init --detect
   ```
   This creates `llll.toml` with your hub's hardware configuration.

4. **Configure your MCP client:**
   - For **Claude Desktop**: The `.mcp.json` in your workspace is automatically detected
   - For **manual setup**: Point your MCP client to run `llll` in your workspace directory

5. **Start building with AI:**
   - Ask Claude to create robot programs (`.py` files)
   - Claude can run programs on your hub and read the output
   - Iterate until your robot does exactly what you want

## Usage

### As an MCP Server

When you run `llll init`, it creates a `.mcp.json` file in your workspace that MCP clients can use:

```json
{
  "mcpServers": {
    "llll": {
      "command": "llll",
      "args": [],
      "env": {}
    }
  }
}
```

The AI agent will have access to these tools:

- `detect_hub` — Auto-detect and configure your LEGO hub
- `get_hub_info` — View hub type, battery, and connected devices
- `run_program` — Execute a MicroPython program on the hub
- `list_programs` — Find `.py` files in the workspace
- `read_log` — Read output from a previous run
- `list_run_logs` — List all available run logs

### Standalone Testing

You can also run the MCP server directly for testing:

```bash
llll
```

## How It Works

### 1. Detect Hardware

```python
# Agent calls:
detect_hub()

# Creates llll.toml with:
# - Hub type (e.g., "InventorHub")
# - Hub Bluetooth name
# - Pybricks firmware version
# - Battery voltage
# - Connected devices on each port
```

If the agent detects an outdated Pybricks version, it can advise you to run `llll flash --check` to see if an update is available.

### 2. Write a Program

The agent creates a MicroPython file (e.g., `motor_test.py`):

```python
from pybricks.hubs import InventorHub
from pybricks.pupdevices import Motor
from pybricks.parameters import Port
from pybricks.tools import wait

hub = InventorHub()
motor = Motor(Port.A)

print("Starting motor test...")
motor.run_angle(500, 360)
print("Motor rotated 360 degrees")
print("Battery:", hub.battery.voltage(), "mV")
```

### 3. Run and Observe

```python
# Agent calls:
run_program("motor_test.py")

# Returns:
# Program: motor_test.py
# Exit code: 0
# Duration: 2.3s
# Log: logs/motor_test_20260211_143052.log
#
# --- Output ---
# Starting motor test...
# Motor rotated 360 degrees
# Battery: 8234 mV
```

### 4. Iterate

The agent reads the output, adjusts the program, and runs it again. Through this loop, the agent can:
- Debug compilation or runtime errors
- Tune motor speeds and sensor thresholds
- Implement complex behaviors
- Test edge cases

## Writing Hub Programs

Programs run on a **constrained MicroPython subset** on the hub. Key differences from regular Python:

### Available Modules

- `pybricks.hubs` — Hub classes (InventorHub, PrimeHub, TechnicHub, etc.)
- `pybricks.pupdevices` — Motor, ColorSensor, UltrasonicSensor, ForceSensor, etc.
- `pybricks.parameters` — Constants (Port, Direction, Stop, Color, Button, Side)
- `pybricks.tools` — wait(), StopWatch, multitask(), run_task()
- `pybricks.robotics` — DriveBase for differential drive
- Standard: `umath`, `urandom`, `ustruct`, `ujson`, `usys`

### Constraints

- **No filesystem** — Cannot read/write files on the hub
- **No networking** — No sockets, HTTP, or WiFi
- **No REPL** — Programs run as batch scripts
- **No `time` module** — Use `pybricks.tools.wait()` and `StopWatch`
- **No `os` or `sys`** — Use `usys` for stdin/stdout
- **RAM-limited** — Keep programs reasonably small
- **`print()` is your telemetry** — All observability comes through print statements

### Async Support

```python
from pybricks.tools import multitask, run_task, wait

async def drive_motors():
    # Drive code here
    ...

async def read_sensors():
    # Sensor code here
    ...

async def main():
    await multitask(drive_motors(), read_sensors())

run_task(main())
```

## Configuration

After running `detect_hub()`, a `llll.toml` file is created:

```toml
[[hubs]]
type = "InventorHub"
name = "MyRobot"
pybricks_version = "3.6.1"
battery_voltage = 8234

[hubs.ports]
A = {device = "SPIKE Large Angular Motor", class = "Motor", id = 49}
B = {device = "Color Sensor", class = "ColorSensor", id = 61}
C = {device = "Ultrasonic Sensor", class = "UltrasonicSensor", id = 62}

[settings]
timeout = 60
```

This tells agents what hardware is available for programming.

## CLI Commands

### `llll init`

Initialize MCP integration for the current directory:

```bash
llll init                    # Create .mcp.json
llll init --detect           # Create .mcp.json and detect hub (creates llll.toml)
llll init --detect --hub-name "MyRobot"  # Detect specific hub by name
```

### `llll flash`

Check for and flash Pybricks firmware updates:

```bash
llll flash --check           # Check if update is available
llll flash                   # Flash latest firmware (interactive, requires confirmation)
```

**Important:** Flashing firmware is a destructive operation that replaces your hub's firmware. The hub must be connected via USB and in DFU mode (hold the button while connecting). This is **not** available as an MCP tool - it must be run manually by the user for safety.

### `llll` (Server Mode)

When run without arguments, starts the MCP server (used by MCP clients):

```bash
llll  # Starts MCP server on stdio
```

## Development

```bash
# Clone the repo
git clone https://github.com/yourusername/llll.git
cd llll

# Install in editable mode
pip install -e .

# Test the init command
mkdir test-workspace && cd test-workspace
llll init

# Or run the server directly
llll
```

## Troubleshooting

**Hub not detected:**
- Ensure the hub has Pybricks firmware installed
- Press the hub button until the light blinks (pairing mode)
- On macOS, use the hub's Bluetooth name: `detect_hub(hub_name="MyHub")`

**Programs timeout:**
- Increase the timeout parameter: `run_program("file.py", timeout=120)`
- Stop programs manually by pressing the hub button

**Import errors in programs:**
- Remember you're writing for MicroPython on the hub, not regular Python
- Use only Pybricks modules and MicroPython built-ins
- Check the [Pybricks documentation](https://docs.pybricks.com/)

## License

MIT

## Credits

Built with [Pybricks](https://pybricks.com/) and [FastMCP](https://github.com/jlowin/fastmcp).
