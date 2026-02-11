"""Firmware version checking and flashing for Pybricks."""

import json
import urllib.request
from pathlib import Path
from typing import Tuple

# Map hub types to firmware filename patterns
HUB_FIRMWARE_MAP = {
    "InventorHub": "primehub",
    "PrimeHub": "primehub",
    "TechnicHub": "technichub",
    "CityHub": "cityhub",
    "EssentialHub": "essentialhub",
    "MoveHub": "movehub",
}

GITHUB_API_URL = "https://api.github.com/repos/pybricks/pybricks-micropython/releases/latest"


def parse_version(version_str: str) -> Tuple[int, ...]:
    """Parse version string to tuple of integers for comparison.

    Examples:
        "3.6.1" -> (3, 6, 1)
        "3.6.0b1" -> (3, 6, 0)  # ignores pre-release suffix
        "unknown" -> (0, 0, 0)
    """
    if not version_str or version_str == "unknown":
        return (0, 0, 0)

    # Remove any pre-release suffixes (e.g., "3.6.0b1" -> "3.6.0")
    version_str = version_str.split("a")[0].split("b")[0].split("rc")[0]

    try:
        parts = version_str.split(".")
        return tuple(int(p) for p in parts)
    except (ValueError, AttributeError):
        return (0, 0, 0)


def compare_versions(current: str, latest: str) -> int:
    """Compare two version strings.

    Returns:
        -1 if current < latest (update available)
         0 if current == latest (up to date)
         1 if current > latest (newer than release)
    """
    current_tuple = parse_version(current)
    latest_tuple = parse_version(latest)

    if current_tuple < latest_tuple:
        return -1
    elif current_tuple > latest_tuple:
        return 1
    else:
        return 0


def get_latest_release() -> dict | None:
    """Fetch latest Pybricks release info from GitHub API.

    Returns:
        Dict with 'version', 'url', 'assets' or None if fetch failed.
    """
    try:
        with urllib.request.urlopen(GITHUB_API_URL, timeout=10) as response:
            data = json.loads(response.read().decode())

            # Extract version from tag (e.g., "v3.6.1" -> "3.6.1")
            tag = data.get("tag_name", "")
            version = tag.lstrip("v")

            return {
                "version": version,
                "url": data.get("html_url"),
                "assets": data.get("assets", []),
                "published_at": data.get("published_at"),
            }
    except Exception as e:
        # Network errors, API rate limits, etc.
        return None


def get_firmware_filename(hub_type: str, version: str) -> str | None:
    """Get the firmware filename for a specific hub type and version.

    Args:
        hub_type: Hub type (e.g., "InventorHub", "TechnicHub")
        version: Version string (e.g., "3.6.1")

    Returns:
        Filename like "pybricks-primehub-v3.6.1.zip" or None if unknown hub type.
    """
    firmware_name = HUB_FIRMWARE_MAP.get(hub_type)
    if not firmware_name:
        return None

    return f"pybricks-{firmware_name}-v{version}.zip"


def get_firmware_download_url(hub_type: str, release_info: dict) -> str | None:
    """Get the download URL for firmware from release assets.

    Args:
        hub_type: Hub type (e.g., "InventorHub")
        release_info: Release info from get_latest_release()

    Returns:
        Download URL or None if not found.
    """
    filename = get_firmware_filename(hub_type, release_info["version"])
    if not filename:
        return None

    for asset in release_info.get("assets", []):
        if asset.get("name") == filename:
            return asset.get("browser_download_url")

    return None


def download_firmware(url: str, destination: Path) -> bool:
    """Download firmware file from URL to destination.

    Args:
        url: Download URL
        destination: Path to save the file

    Returns:
        True if successful, False otherwise.
    """
    try:
        with urllib.request.urlopen(url, timeout=60) as response:
            destination.write_bytes(response.read())
        return True
    except Exception:
        return False


def check_update_available(current_version: str, hub_type: str) -> dict:
    """Check if a firmware update is available.

    Args:
        current_version: Currently installed version (e.g., "3.5.0")
        hub_type: Hub type (e.g., "InventorHub")

    Returns:
        Dict with 'available', 'current', 'latest', 'download_url', 'release_url'
    """
    release = get_latest_release()

    if not release:
        return {
            "available": False,
            "current": current_version,
            "latest": None,
            "error": "Could not fetch latest release from GitHub",
        }

    latest_version = release["version"]
    comparison = compare_versions(current_version, latest_version)

    result = {
        "available": comparison < 0,
        "current": current_version,
        "latest": latest_version,
        "release_url": release["url"],
    }

    if comparison < 0:
        # Update available - get download URL
        download_url = get_firmware_download_url(hub_type, release)
        result["download_url"] = download_url

    return result
