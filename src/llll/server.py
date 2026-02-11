"""llll MCP server — gives agents the ability to run programs on LEGO hubs."""

from pathlib import Path

from mcp.server.fastmcp import FastMCP

from . import config, discover, logs, runner

server = FastMCP(
    "llll",
    instructions=(
        "llll (LEGO lin la loop) lets you run MicroPython programs on LEGO hubs "
        "via Pybricks. Start by calling get_hub_info to understand the hardware, "
        "or detect_hub if no llll.toml config exists yet. Then write .py files "
        "and run them with run_program. print() is your only telemetry — use it "
        "generously. Programs run on a constrained MicroPython subset: no "
        "filesystem, no networking, no REPL. Key modules: pybricks.hubs, "
        "pybricks.pupdevices, pybricks.parameters, pybricks.tools, "
        "pybricks.robotics."
    ),
)

PROJECT_DIR = Path.cwd()


def _default_hub_name() -> str | None:
    """Get the default hub name from config, if set."""
    cfg = config.load_config(PROJECT_DIR)
    if cfg and cfg.get("hubs"):
        # Use first hub's name
        hub = cfg["hubs"][0]
        return hub.get("name")
    return None


@server.tool()
async def detect_hub(hub_name: str | None = None) -> str:
    """Detect the connected LEGO hub and what devices are plugged into its ports.

    Runs a discovery program on the hub via Bluetooth, then saves the results
    to llll.toml so other tools know what hardware is available.

    Call this once when setting up a new project, or whenever the hardware
    configuration changes (different motors/sensors plugged in).

    Args:
        hub_name: Bluetooth name of the hub to detect (optional).
    """
    data = await discover.run_discovery(PROJECT_DIR, hub_name=hub_name)

    if "error" in data:
        msg = f"Detection failed: {data['error']}"
        if data.get("output"):
            msg += f"\n\nRaw output:\n{data['output']}"
        return msg

    # Save to config
    cfg = config.discovery_to_config(data)
    path = config.save_config(PROJECT_DIR, cfg)

    summary = config.format_hub_info(cfg)
    return f"Hub detected and saved to {path.name}:\n\n{summary}"


@server.tool()
def get_hub_info() -> str:
    """Get information about the configured LEGO hub(s) and connected devices.

    Returns hub type, name, battery level, and what motors/sensors are
    connected to which ports. This tells you what hardware you can use
    in your programs.

    If no config exists yet, call detect_hub first.
    """
    cfg = config.load_config(PROJECT_DIR)
    if cfg is None:
        return (
            "No llll.toml found. Call detect_hub to auto-detect the connected "
            "hub and its devices."
        )

    return config.format_hub_info(cfg)


@server.tool()
async def run_program(
    file: str,
    hub_name: str | None = None,
    timeout: int = 60,
) -> str:
    """Run a MicroPython program on the LEGO hub via Bluetooth.

    Compiles, uploads, and executes the program, then returns the captured output.
    The program's print() statements are the primary way to get data back from the hub.

    Args:
        file: Path to the .py file, relative to the project root.
        hub_name: Bluetooth name of the hub (optional, uses config default if set).
        timeout: Max seconds to wait for the program to complete. Default 60.
    """
    if hub_name is None:
        hub_name = _default_hub_name()

    result = await runner.run_program(file, PROJECT_DIR, hub_name, timeout)

    if result.get("error"):
        return f"Error: {result['error']}"

    parts = [f"Program: {file}"]

    if result["timed_out"]:
        parts.append(f"TIMED OUT after {result['duration']:.1f}s")
    else:
        parts.append(f"Exit code: {result['exit_code']}")
        parts.append(f"Duration: {result['duration']:.1f}s")

    parts.append(f"Log: {result['log_file']}")
    parts.append("")
    parts.append("--- Output ---")
    parts.append(result["output"])

    return "\n".join(parts)


@server.tool()
def list_programs(directory: str = ".") -> str:
    """List MicroPython (.py) program files in the project.

    Args:
        directory: Directory to search, relative to the project root. Default: project root.
    """
    search_dir = PROJECT_DIR / directory
    if not search_dir.exists():
        return f"Directory not found: {directory}"

    py_files = sorted(search_dir.rglob("*.py"))
    if not py_files:
        return f"No .py files found in {directory}"

    lines = []
    for f in py_files:
        rel = f.relative_to(PROJECT_DIR)
        rel_str = str(rel)
        if any(part.startswith(".") for part in rel.parts):
            continue
        if "venv" in rel.parts or "__pycache__" in rel.parts:
            continue
        lines.append(str(rel))

    if not lines:
        return f"No .py files found in {directory}"

    return "\n".join(lines)


@server.tool()
def read_log(log_name: str | None = None) -> str:
    """Read a log file from a previous run.

    Args:
        log_name: Filename of the log (e.g. "hello_20260211_152707.log").
                  Omit to read the most recent log.
    """
    return logs.read_log(PROJECT_DIR, log_name)


@server.tool()
def list_run_logs() -> str:
    """List all run log files, most recent first."""
    entries = logs.list_logs(PROJECT_DIR)
    if not entries:
        return "No logs yet."

    lines = []
    for entry in entries:
        lines.append(f"{entry['file']}  ({entry['size']} bytes)")
    return "\n".join(lines)


def main():
    server.run()


if __name__ == "__main__":
    main()
