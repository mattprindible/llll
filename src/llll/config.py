"""Configuration management for llll.toml."""

import tomllib
from pathlib import Path

CONFIG_FILENAME = "llll.toml"


def config_path(project_dir: Path) -> Path:
    return project_dir / CONFIG_FILENAME


def load_config(project_dir: Path) -> dict | None:
    """Load llll.toml if it exists. Returns None if not found."""
    path = config_path(project_dir)
    if not path.exists():
        return None
    with open(path, "rb") as f:
        return tomllib.load(f)


def save_config(project_dir: Path, data: dict) -> Path:
    """Write config data to llll.toml. Returns the path written."""
    path = config_path(project_dir)
    lines = []

    # Top-level settings
    settings = data.get("settings", {})
    if settings:
        lines.append("[settings]")
        for k, v in settings.items():
            lines.append(f"{k} = {_toml_value(v)}")
        lines.append("")

    # Hubs
    for hub in data.get("hubs", []):
        lines.append("[[hubs]]")
        lines.append(f"type = {_toml_value(hub['type'])}")
        if hub.get("name"):
            lines.append(f"name = {_toml_value(hub['name'])}")
        if hub.get("battery_voltage"):
            lines.append(f"battery_voltage = {hub['battery_voltage']}")
        lines.append("")

        # Ports
        ports = hub.get("ports", {})
        if ports:
            lines.append(f"[hubs.ports]")
            for port_letter, port_info in sorted(ports.items()):
                if isinstance(port_info, dict):
                    lines.append(
                        f'{port_letter} = {{device = {_toml_value(port_info["device"])}'
                        f', class = {_toml_value(port_info["class"])}'
                        f', id = {port_info["id"]}}}'
                    )
                else:
                    lines.append(f"{port_letter} = {_toml_value(port_info)}")
            lines.append("")

    path.write_text("\n".join(lines) + "\n")
    return path


def discovery_to_config(discovery_data: dict) -> dict:
    """Convert discovery output to config format."""
    ports = {}
    for port_info in discovery_data.get("ports", []):
        letter = port_info["port"]
        if port_info.get("device_id") is not None:
            ports[letter] = {
                "device": port_info.get("device_name", f"Unknown ID {port_info['device_id']}"),
                "class": port_info.get("pybricks_class", "PUPDevice"),
                "id": port_info["device_id"],
            }

    hub = {
        "type": discovery_data["hub_type"],
        "name": discovery_data.get("hub_name"),
        "battery_voltage": discovery_data.get("battery_voltage"),
        "ports": ports,
    }

    return {
        "hubs": [hub],
        "settings": {
            "timeout": 60,
        },
    }


def format_hub_info(cfg: dict) -> str:
    """Format config into a human/agent-readable summary."""
    lines = []
    for i, hub in enumerate(cfg.get("hubs", [])):
        if i > 0:
            lines.append("")
        lines.append(f"Hub: {hub['type']}")
        if hub.get("name"):
            lines.append(f"Name: {hub['name']}")
        if hub.get("battery_voltage"):
            lines.append(f"Battery: {hub['battery_voltage']} mV")

        ports = hub.get("ports", {})
        if ports:
            lines.append("Ports:")
            for letter in sorted(ports.keys()):
                info = ports[letter]
                if isinstance(info, dict):
                    lines.append(f"  {letter}: {info['device']} ({info['class']})")
                else:
                    lines.append(f"  {letter}: {info}")
        else:
            lines.append("Ports: none detected")

    settings = cfg.get("settings", {})
    if settings:
        lines.append("")
        lines.append("Settings:")
        for k, v in settings.items():
            lines.append(f"  {k}: {v}")

    return "\n".join(lines)


def _toml_value(v) -> str:
    """Format a Python value as a TOML literal."""
    if isinstance(v, str):
        return f'"{v}"'
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        return str(v)
    return f'"{v}"'
