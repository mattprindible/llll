"""Command-line interface for llll."""

import argparse
import json
import sys
from pathlib import Path


def init_workspace(detect: bool = False, hub_name: str | None = None) -> int:
    """Initialize a workspace for llll MCP integration.

    Creates:
    - .mcp.json for MCP client configuration
    - llll.toml (if --detect is used)

    Args:
        detect: Whether to run hub detection immediately
        hub_name: Hub name for detection (optional)

    Returns:
        Exit code (0 = success)
    """
    cwd = Path.cwd()

    print("Initializing llll MCP workspace...")
    print(f"Location: {cwd}")
    print()

    # Create .mcp.json
    mcp_config_path = cwd / ".mcp.json"
    if mcp_config_path.exists():
        print("⚠️  .mcp.json already exists")
        response = input("Overwrite? [y/N]: ").strip().lower()
        if response != "y":
            print("Skipping .mcp.json creation")
        else:
            _create_mcp_json(mcp_config_path, cwd)
    else:
        _create_mcp_json(mcp_config_path, cwd)

    print()

    # Optionally run detection
    if detect:
        print("Running hub detection...")
        print()
        try:
            import asyncio
            from . import config, discover

            async def run_detect():
                data = await discover.run_discovery(cwd, hub_name=hub_name)

                if "error" in data:
                    print(f"❌ Detection failed: {data['error']}")
                    if data.get("output"):
                        print(f"\nRaw output:\n{data['output']}")
                    return False

                cfg = config.discovery_to_config(data)
                path = config.save_config(cwd, cfg)

                summary = config.format_hub_info(cfg)
                print(f"✓ Hub detected and saved to {path.name}")
                print()
                print(summary)
                print()
                return True

            success = asyncio.run(run_detect())
            if not success:
                print()
                print("You can run detection later with: llll init --detect")
                return 1

        except Exception as e:
            print(f"❌ Detection failed: {e}")
            print()
            print("You can run detection later with: llll init --detect")
            return 1
    else:
        print("MCP workspace initialized!")
        print()
        print("Next steps:")
        print("  1. Configure your MCP client to use this workspace")
        print("  2. Run 'llll init --detect' to auto-detect your LEGO hub (optional)")
        print("  3. Start building robot programs with your AI agent")
        print()

    return 0


def flash_firmware(check_only: bool = False, hub_name: str | None = None) -> int:
    """Flash Pybricks firmware to a LEGO hub.

    Args:
        check_only: Only check for updates, don't flash
        hub_name: Hub name for flashing (optional)

    Returns:
        Exit code (0 = success)
    """
    import subprocess
    import tempfile
    from . import config, firmware

    cwd = Path.cwd()

    # Load config to get hub info
    cfg = config.load_config(cwd)
    if not cfg or not cfg.get("hubs"):
        print("❌ No hub configuration found.")
        print()
        print("Run 'llll init --detect' first to detect your hub.")
        return 1

    hub = cfg["hubs"][0]
    hub_type = hub.get("type")
    current_version = hub.get("pybricks_version", "unknown")

    print(f"Hub: {hub_type}")
    print(f"Current Pybricks version: {current_version}")
    print()

    # Check for updates
    print("Checking for firmware updates...")
    update_info = firmware.check_update_available(current_version, hub_type)

    if "error" in update_info:
        print(f"❌ {update_info['error']}")
        return 1

    latest_version = update_info["latest"]
    print(f"Latest Pybricks version: {latest_version}")
    print()

    if not update_info["available"]:
        print("✓ Your Pybricks firmware is up to date!")
        return 0

    if check_only:
        print(f"⚠️  Update available: {current_version} → {latest_version}")
        print()
        print(f"Release: {update_info['release_url']}")
        print()
        print("To update, run: llll flash")
        return 0

    # Update is available - proceed with flashing
    print(f"⚠️  Update available: {current_version} → {latest_version}")
    print()
    print("This will flash new firmware to your LEGO hub.")
    print()
    print("⚠️  WARNING: This is a destructive operation!")
    print("   - Replaces existing firmware")
    print("   - Hub must be in DFU mode (hold button while connecting USB)")
    print("   - Do not disconnect during flashing")
    print()

    response = input("Continue? [y/N]: ").strip().lower()
    if response != "y":
        print("Cancelled.")
        return 1

    # Download firmware
    download_url = update_info.get("download_url")
    if not download_url:
        print(f"❌ Could not find firmware download for {hub_type}")
        return 1

    print()
    print(f"Downloading firmware...")
    print(f"URL: {download_url}")

    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        success = firmware.download_firmware(download_url, tmp_path)
        if not success:
            print("❌ Download failed")
            return 1

        print(f"✓ Downloaded to {tmp_path}")
        print()

        # Flash firmware using pybricksdev
        print("Flashing firmware...")
        print()
        print("Make sure your hub is:")
        print("  1. Connected via USB")
        print("  2. In DFU mode (hold button while connecting)")
        print()

        response = input("Hub ready? [y/N]: ").strip().lower()
        if response != "y":
            print("Cancelled.")
            return 1

        print()
        cmd = ["pybricksdev", "flash", str(tmp_path)]
        result = subprocess.run(cmd)

        if result.returncode == 0:
            print()
            print("✓ Firmware flashed successfully!")
            print()
            print("Next steps:")
            print("  1. Disconnect and reconnect your hub")
            print("  2. Run 'llll init --detect' to update configuration")
            return 0
        else:
            print()
            print("❌ Flashing failed")
            print()
            print("Common issues:")
            print("  - Hub not in DFU mode (hold button while connecting USB)")
            print("  - USB connection issues")
            print("  - pybricksdev not installed (pip install pybricksdev)")
            return 1

    finally:
        # Clean up temp file
        if tmp_path.exists():
            tmp_path.unlink()


def _create_mcp_json(path: Path, cwd: Path):
    """Create .mcp.json configuration file."""
    config = {
        "mcpServers": {
            "llll": {
                "command": "llll",
                "args": [],
                "env": {}
            }
        }
    }

    path.write_text(json.dumps(config, indent=2) + "\n")
    print(f"✓ Created {path.relative_to(cwd)}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="llll",
        description="LEGO lin la loop — MCP server for LEGO Mindstorms via Pybricks",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # llll init
    init_parser = subparsers.add_parser(
        "init",
        help="Initialize a workspace for llll development",
    )
    init_parser.add_argument(
        "--detect",
        action="store_true",
        help="Run hub detection after initialization",
    )
    init_parser.add_argument(
        "--hub-name",
        type=str,
        help="Bluetooth name of the hub for detection",
    )

    # llll flash
    flash_parser = subparsers.add_parser(
        "flash",
        help="Flash Pybricks firmware to a LEGO hub",
    )
    flash_parser.add_argument(
        "--check",
        action="store_true",
        help="Only check for updates, don't flash",
    )
    flash_parser.add_argument(
        "--hub-name",
        type=str,
        help="Bluetooth name of the hub (optional)",
    )

    args = parser.parse_args()

    if args.command == "init":
        return init_workspace(detect=args.detect, hub_name=args.hub_name)
    elif args.command == "flash":
        return flash_firmware(check_only=args.check, hub_name=getattr(args, "hub_name", None))
    else:
        # No subcommand = run the MCP server
        from .server import main as server_main
        server_main()
        return 0


if __name__ == "__main__":
    sys.exit(main())
