"""Hub discovery — detect hub type, name, battery, and connected devices."""

import json
import re
from pathlib import Path

from . import runner

# Device ID → (human name, pybricks class, module)
DEVICE_MAP = {
    1: ("Powered Up Medium Motor", "DCMotor", "pybricks.pupdevices"),
    2: ("Powered Up Train Motor", "DCMotor", "pybricks.pupdevices"),
    8: ("Powered Up Light", "Light", "pybricks.pupdevices"),
    34: ("WeDo 2.0 Tilt Sensor", "TiltSensor", "pybricks.pupdevices"),
    35: ("WeDo 2.0 Motion Sensor", "InfraredSensor", "pybricks.pupdevices"),
    37: ("BOOST Color Distance Sensor", "ColorDistanceSensor", "pybricks.pupdevices"),
    38: ("BOOST Interactive Motor", "Motor", "pybricks.pupdevices"),
    46: ("Technic Large Motor", "Motor", "pybricks.pupdevices"),
    47: ("Technic XL Motor", "Motor", "pybricks.pupdevices"),
    48: ("SPIKE Medium Angular Motor", "Motor", "pybricks.pupdevices"),
    49: ("SPIKE Large Angular Motor", "Motor", "pybricks.pupdevices"),
    61: ("Color Sensor", "ColorSensor", "pybricks.pupdevices"),
    62: ("Ultrasonic Sensor", "UltrasonicSensor", "pybricks.pupdevices"),
    63: ("Force Sensor", "ForceSensor", "pybricks.pupdevices"),
    64: ("3x3 Color Light Matrix", "ColorLightMatrix", "pybricks.pupdevices"),
    65: ("Technic Small Angular Motor", "Motor", "pybricks.pupdevices"),
    75: ("Technic Medium Angular Motor", "Motor", "pybricks.pupdevices"),
    76: ("Technic Large Angular Motor", "Motor", "pybricks.pupdevices"),
}

# The MicroPython program that runs on the hub to detect everything.
# Output is a single line: LLLL_DETECT:<json>
DISCOVERY_PROGRAM = '''\
import ujson
from pybricks.iodevices import PUPDevice
from pybricks.parameters import Port
from uerrno import ENODEV

# --- Detect hub type ---
hub = None
hub_type = "Unknown"

for name in ["InventorHub", "PrimeHub", "TechnicHub", "CityHub", "EssentialHub", "MoveHub"]:
    try:
        mod = __import__("pybricks.hubs", None, None, [name])
        cls = getattr(mod, name)
        hub = cls()
        hub_type = name
        break
    except (ImportError, AttributeError, OSError):
        pass

if hub is None:
    print("LLLL_DETECT:" + ujson.dumps({"error": "Could not detect hub type"}))
    raise SystemExit

# --- Hub info ---
hub_name = hub.system.name()
battery_mv = hub.battery.voltage()

# --- Scan ports ---
ports = []
for letter in ["A", "B", "C", "D", "E", "F"]:
    try:
        port = getattr(Port, letter)
    except AttributeError:
        break
    try:
        dev = PUPDevice(port)
        dev_id = dev.info()["id"]
        ports.append({"port": letter, "device_id": dev_id})
    except OSError as ex:
        if ex.args[0] == ENODEV:
            ports.append({"port": letter, "device_id": None})
        else:
            ports.append({"port": letter, "device_id": None, "error": str(ex)})

result = {
    "hub_type": hub_type,
    "hub_name": hub_name,
    "battery_voltage": battery_mv,
    "ports": ports,
}

print("LLLL_DETECT:" + ujson.dumps(result))
'''


def parse_discovery_output(output: str) -> dict | None:
    """Parse the structured output from the discovery program."""
    for line in output.splitlines():
        if line.startswith("LLLL_DETECT:"):
            payload = line[len("LLLL_DETECT:"):]
            data = json.loads(payload)

            if "error" in data:
                return data

            # Enrich port data with human-readable names
            for port_info in data.get("ports", []):
                dev_id = port_info.get("device_id")
                if dev_id is not None and dev_id in DEVICE_MAP:
                    name, cls, mod = DEVICE_MAP[dev_id]
                    port_info["device_name"] = name
                    port_info["pybricks_class"] = cls
                    port_info["pybricks_module"] = mod
                elif dev_id is not None:
                    port_info["device_name"] = f"Unknown (ID {dev_id})"

            return data

    return None


async def run_discovery(
    project_dir: Path,
    hub_name: str | None = None,
    timeout: int = 30,
) -> dict:
    """Run the discovery program on the hub and return parsed results."""
    # Write the discovery program to a temp file
    discover_file = project_dir / "_llll_discover.py"
    try:
        discover_file.write_text(DISCOVERY_PROGRAM)

        result = await runner.run_program(
            str(discover_file.relative_to(project_dir)),
            project_dir,
            hub_name=hub_name,
            timeout=timeout,
        )

        if result.get("error"):
            return {"error": result["error"]}

        if not result["success"]:
            return {
                "error": f"Discovery program failed (exit code {result.get('exit_code')})",
                "output": result.get("output", ""),
            }

        parsed = parse_discovery_output(result["output"])
        if parsed is None:
            return {
                "error": "Could not parse discovery output",
                "output": result.get("output", ""),
            }

        return parsed

    finally:
        if discover_file.exists():
            discover_file.unlink()
