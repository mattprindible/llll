"""Log file management for llll runs."""

from pathlib import Path


def list_logs(project_dir: Path) -> list[dict]:
    """List all log files, most recent first."""
    logs_dir = project_dir / "logs"
    if not logs_dir.exists():
        return []

    logs = []
    for f in sorted(logs_dir.glob("*.log"), reverse=True):
        if f.name == "latest.log":
            continue
        logs.append({
            "file": f.name,
            "size": f.stat().st_size,
        })
    return logs


def read_log(project_dir: Path, log_name: str | None = None) -> str:
    """Read a log file. Reads latest.log if no name specified."""
    logs_dir = project_dir / "logs"

    if log_name:
        log_file = logs_dir / log_name
    else:
        log_file = logs_dir / "latest.log"

    if not log_file.exists():
        if log_name:
            return f"Log not found: {log_name}"
        return "No logs yet. Run a program first."

    return log_file.read_text()
