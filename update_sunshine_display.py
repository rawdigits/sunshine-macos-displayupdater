#!/usr/bin/env python3
"""
Sunshine Display Updater
Automatically updates Sunshine's display configuration based on display name.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path


def get_displays():
    """Get all displays from system_profiler."""
    try:
        result = subprocess.run(
            ["system_profiler", "SPDisplaysDataType", "-json"],
            capture_output=True,
            text=True,
            check=True
        )
        data = json.loads(result.stdout)

        displays = []
        for gpu in data.get("SPDisplaysDataType", []):
            for display in gpu.get("spdisplays_ndrvs", []):
                display_info = {
                    "name": display.get("_name", "Unknown"),
                    "id": display.get("_spdisplays_displayID", ""),
                    "resolution": display.get("_spdisplays_resolution", ""),
                    "pixels": display.get("_spdisplays_pixels", ""),
                    "is_main": display.get("spdisplays_main") == "spdisplays_yes",
                    "is_online": display.get("spdisplays_online") == "spdisplays_yes"
                }
                displays.append(display_info)

        return displays
    except subprocess.CalledProcessError as e:
        print(f"Error running system_profiler: {e}", file=sys.stderr)
        return []
    except json.JSONDecodeError as e:
        print(f"Error parsing system_profiler output: {e}", file=sys.stderr)
        return []


def find_display_by_name(display_name):
    """Find a display by name (case-insensitive, partial match)."""
    displays = get_displays()
    display_name_lower = display_name.lower()

    # First try exact match
    for display in displays:
        if display["name"].lower() == display_name_lower:
            return display

    # Then try partial match
    for display in displays:
        if display_name_lower in display["name"].lower():
            return display

    return None


def get_sunshine_config_path():
    """Get the path to Sunshine configuration file."""
    config_path = Path.home() / ".config" / "sunshine" / "sunshine.conf"
    return config_path


def update_sunshine_config(display_id):
    """Update Sunshine configuration with new display ID."""
    config_path = get_sunshine_config_path()

    # Ensure config directory exists
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Read existing config if it exists
    if config_path.exists():
        with open(config_path, 'r') as f:
            content = f.read()
    else:
        content = ""

    # Update or add output_name setting
    output_name_pattern = r'^output_name\s*=\s*.*$'
    new_line = f"output_name = {display_id}"

    if re.search(output_name_pattern, content, re.MULTILINE):
        # Replace existing line
        new_content = re.sub(output_name_pattern, new_line, content, flags=re.MULTILINE)
    else:
        # Add new line
        if content and not content.endswith('\n'):
            content += '\n'
        new_content = content + new_line + '\n'

    # Write updated config
    with open(config_path, 'w') as f:
        f.write(new_content)

    return config_path


def detect_sunshine_service():
    """Detect which sunshine service is installed."""
    try:
        result = subprocess.run(
            ["brew", "services", "list"],
            capture_output=True,
            text=True
        )
        if "sunshine-beta" in result.stdout:
            return "sunshine-beta"
        elif "sunshine" in result.stdout:
            return "sunshine"
    except Exception:
        pass
    return None


def is_sunshine_running():
    """Check if Sunshine process is currently running."""
    try:
        result = subprocess.run(
            ["pgrep", "-x", "sunshine"],
            capture_output=True
        )
        return result.returncode == 0
    except Exception:
        return False


def ensure_sunshine_running():
    """Ensure Sunshine service is running, start it if not."""
    if is_sunshine_running():
        return True, "Sunshine already running"

    # Sunshine is not running, try to start it
    sunshine_service = detect_sunshine_service()

    # Try to start via brew services
    if sunshine_service:
        try:
            result = subprocess.run(
                ["brew", "services", "start", sunshine_service],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return True, f"Started via brew services ({sunshine_service})"
        except Exception:
            pass

    # Try to start via launchctl
    try:
        result = subprocess.run(["id", "-u"], capture_output=True, text=True)
        uid = result.stdout.strip()

        for service_name in ["homebrew.mxcl.sunshine-beta", "homebrew.mxcl.sunshine"]:
            result = subprocess.run(
                ["launchctl", "start", f"gui/{uid}/{service_name}"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return True, f"Started via launchctl ({service_name})"
    except Exception:
        pass

    return False, "Could not start Sunshine"


def restart_sunshine():
    """Attempt to restart Sunshine service."""
    # Detect which version is installed (sunshine or sunshine-beta)
    sunshine_service = detect_sunshine_service()

    # Try to restart via brew services
    if sunshine_service:
        try:
            result = subprocess.run(
                ["brew", "services", "restart", sunshine_service],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return True, f"Restarted via brew services ({sunshine_service})"
        except FileNotFoundError:
            pass

    # Try to restart via launchctl (if installed via homebrew)
    for service_name in ["homebrew.mxcl.sunshine-beta", "homebrew.mxcl.sunshine"]:
        try:
            result = subprocess.run(
                ["launchctl", "kickstart", "-k", f"gui/$(id -u)/{service_name}"],
                capture_output=True,
                text=True,
                shell=True
            )
            if result.returncode == 0:
                return True, f"Restarted via launchctl kickstart ({service_name})"
        except Exception:
            pass

    # Try to find and kill/restart sunshine process via launchctl
    try:
        # Get current user ID
        result = subprocess.run(["id", "-u"], capture_output=True, text=True)
        uid = result.stdout.strip()

        for service_name in ["homebrew.mxcl.sunshine-beta", "homebrew.mxcl.sunshine"]:
            # Stop the service
            stop_result = subprocess.run(
                ["launchctl", "stop", f"gui/{uid}/{service_name}"],
                capture_output=True
            )

            # Start the service
            start_result = subprocess.run(
                ["launchctl", "start", f"gui/{uid}/{service_name}"],
                capture_output=True,
                text=True
            )

            if start_result.returncode == 0:
                return True, f"Restarted via launchctl stop/start ({service_name})"
    except Exception:
        pass

    # Last resort: kill the process (will auto-restart if managed by launchd)
    try:
        subprocess.run(["pkill", "-x", "sunshine"], check=False)
        return True, "Sent kill signal (service should auto-restart)"
    except Exception as e:
        return False, f"Could not restart: {e}"


def main():
    if len(sys.argv) < 2:
        print("Usage: update_sunshine_display.py <display_name> [--no-restart]")
        print("\nAvailable displays:")
        displays = get_displays()
        for display in displays:
            status = " (main)" if display["is_main"] else ""
            online = " [online]" if display["is_online"] else " [offline]"
            print(f"  - {display['name']}{status}{online}")
            print(f"    ID: {display['id']}, Resolution: {display['resolution']}")
        sys.exit(1)

    display_name = sys.argv[1]
    no_restart = "--no-restart" in sys.argv

    # Find the display
    display = find_display_by_name(display_name)

    if not display:
        print(f"Error: Display '{display_name}' not found", file=sys.stderr)
        print("\nAvailable displays:", file=sys.stderr)
        displays = get_displays()
        for d in displays:
            print(f"  - {d['name']} (ID: {d['id']})", file=sys.stderr)
        sys.exit(1)

    print(f"Found display: {display['name']}")
    print(f"  ID: {display['id']}")
    print(f"  Resolution: {display['resolution']}")
    print(f"  Pixels: {display['pixels']}")

    # Update Sunshine config
    config_path = update_sunshine_config(display['id'])
    print(f"\nUpdated {config_path}")
    print(f"Set output_name = {display['id']}")

    # Restart Sunshine if requested
    if not no_restart:
        print("\nRestarting Sunshine...")
        success, message = restart_sunshine()
        if success:
            print(f"  {message}")
        else:
            print(f"  Warning: {message}", file=sys.stderr)
            print("  You may need to restart Sunshine manually", file=sys.stderr)
    else:
        print("\nSkipped restart (--no-restart specified)")
        print("Remember to restart Sunshine for changes to take effect")


if __name__ == "__main__":
    main()
