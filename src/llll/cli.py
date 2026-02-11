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

    args = parser.parse_args()

    if args.command == "init":
        return init_workspace(detect=args.detect, hub_name=args.hub_name)
    else:
        # No subcommand = run the MCP server
        from .server import main as server_main
        server_main()
        return 0


if __name__ == "__main__":
    sys.exit(main())
