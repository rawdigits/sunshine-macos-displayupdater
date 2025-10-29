#!/usr/bin/env python3
"""
Automatic Sunshine Display Updater
Reads target display from config file and updates Sunshine configuration.
Designed to be run periodically via launchd.
"""

import json
import os
import sys
from pathlib import Path

# Import the main update script functions
sys.path.insert(0, str(Path(__file__).parent))
from update_sunshine_display import find_display_by_name, update_sunshine_config, restart_sunshine


def get_config_path():
    """Get path to display config file."""
    script_dir = Path(__file__).parent
    return script_dir / "display_config.json"


def load_config():
    """Load configuration from JSON file."""
    config_path = get_config_path()

    if not config_path.exists():
        print(f"Error: Config file not found at {config_path}", file=sys.stderr)
        print("Please create a display_config.json file with:", file=sys.stderr)
        print('  {"target_display": "Your Display Name"}', file=sys.stderr)
        sys.exit(1)

    try:
        with open(config_path, 'r') as f:
            config = json.load(f)

        if "target_display" not in config:
            print("Error: 'target_display' not specified in config", file=sys.stderr)
            sys.exit(1)

        return config
    except json.JSONDecodeError as e:
        print(f"Error parsing config file: {e}", file=sys.stderr)
        sys.exit(1)


def get_current_sunshine_display():
    """Get the currently configured display ID from Sunshine."""
    from pathlib import Path
    import re

    config_path = Path.home() / ".config" / "sunshine" / "sunshine.conf"

    if not config_path.exists():
        return None

    try:
        with open(config_path, 'r') as f:
            content = f.read()

        match = re.search(r'^output_name\s*=\s*(\S+)', content, re.MULTILINE)
        if match:
            return match.group(1)
    except Exception as e:
        print(f"Warning: Could not read current config: {e}", file=sys.stderr)

    return None


def main():
    # Load configuration
    config = load_config()
    target_display_name = config["target_display"]
    no_restart = "--no-restart" in sys.argv or config.get("no_auto_restart", False)

    print(f"Target display: {target_display_name}")

    # Find the display
    display = find_display_by_name(target_display_name)

    if not display:
        print(f"Warning: Display '{target_display_name}' not found", file=sys.stderr)
        print("Sunshine configuration not updated", file=sys.stderr)
        sys.exit(1)

    print(f"Found display: {display['name']}")
    print(f"  ID: {display['id']}")
    print(f"  Resolution: {display['resolution']}")

    # Check if update is needed
    current_id = get_current_sunshine_display()
    if current_id == display['id']:
        print(f"\nDisplay ID hasn't changed (still {display['id']})")
        print("No update needed")
        sys.exit(0)

    print(f"\nDisplay ID changed: {current_id} -> {display['id']}")

    # Update Sunshine config
    config_path = update_sunshine_config(display['id'])
    print(f"Updated {config_path}")

    # Restart Sunshine if requested
    if not no_restart:
        print("\nRestarting Sunshine...")
        success, message = restart_sunshine()
        if success:
            print(f"  {message}")
        else:
            print(f"  Warning: {message}", file=sys.stderr)
    else:
        print("\nSkipped restart")


if __name__ == "__main__":
    main()
