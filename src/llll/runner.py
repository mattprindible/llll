"""Run MicroPython programs on a LEGO hub via pybricksdev."""

import asyncio
from datetime import datetime, timezone
from pathlib import Path


async def run_program(
    file_path: str,
    project_dir: Path,
    hub_name: str | None = None,
    timeout: int = 60,
) -> dict:
    """Compile, upload, and run a MicroPython program on the hub.

    Returns a dict with: success, exit_code, timed_out, duration, output, log_file, error.
    """
    program = project_dir / file_path
    if not program.exists():
        return {
            "success": False,
            "error": f"File not found: {file_path}",
            "output": "",
            "log_file": None,
        }

    # Ensure logs directory exists
    logs_dir = project_dir / "logs"
    logs_dir.mkdir(exist_ok=True)

    # Log file path
    program_name = program.stem
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    log_file = logs_dir / f"{program_name}_{ts}.log"

    # Build the pybricksdev command
    cmd = ["pybricksdev", "run", "ble"]
    if hub_name:
        cmd.extend(["--name", hub_name])
    cmd.append(str(program))

    start_time = datetime.now(timezone.utc)

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
    except FileNotFoundError:
        return {
            "success": False,
            "error": "pybricksdev not found. Install it with: pip install pybricksdev",
            "output": "",
            "log_file": None,
        }

    timed_out = False
    try:
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        output = stdout.decode("utf-8", errors="replace")
        exit_code = proc.returncode
    except asyncio.TimeoutError:
        proc.kill()
        stdout, _ = await proc.communicate()
        output = stdout.decode("utf-8", errors="replace")
        exit_code = -1
        timed_out = True

    end_time = datetime.now(timezone.utc)
    duration = (end_time - start_time).total_seconds()

    # Write log file
    with open(log_file, "w") as f:
        f.write("=== llll run log ===\n")
        f.write(f"program: {file_path}\n")
        f.write(f"timestamp: {start_time.isoformat()}\n")
        if hub_name:
            f.write(f"hub: {hub_name}\n")
        f.write("=== output ===\n")
        f.write(output)
        if not output.endswith("\n"):
            f.write("\n")
        f.write("=== end ===\n")
        f.write(f"exit_code: {exit_code}\n")
        f.write(f"duration: {duration:.1f}s\n")
        f.write(f"timed_out: {timed_out}\n")
        f.write(f"finished: {end_time.isoformat()}\n")

    # Update latest.log symlink
    latest = logs_dir / "latest.log"
    if latest.is_symlink() or latest.exists():
        latest.unlink()
    latest.symlink_to(log_file.name)

    return {
        "success": exit_code == 0,
        "exit_code": exit_code,
        "timed_out": timed_out,
        "duration": duration,
        "output": output,
        "log_file": str(log_file.relative_to(project_dir)),
    }
