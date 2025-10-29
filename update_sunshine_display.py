#!/usr/bin/env python3
"""
Sunshine Display Manager
Automatically updates Sunshine's display configuration based on display name.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path


def get_config_path():
    """Get path to display config file."""
    script_dir = Path(__file__).parent
    return script_dir / "display_config.json"


def load_config():
    """Load configuration from JSON file."""
    config_path = get_config_path()

    if not config_path.exists():
        return None

    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error parsing config file: {e}", file=sys.stderr)
        return None


def get_displays(retries=3, retry_delay=0.5):
    """Get all displays from system_profiler with retries."""
    import time

    for attempt in range(retries):
        try:
            result = subprocess.run(
                ["system_profiler", "SPDisplaysDataType", "-json"],
                capture_output=True,
                text=True,
                check=True,
                timeout=10
            )

            if not result.stdout.strip():
                if attempt < retries - 1:
                    time.sleep(retry_delay)
                    continue
                return []

            data = json.loads(result.stdout)

            displays = []
            for gpu in data.get("SPDisplaysDataType", []):
                for display in gpu.get("spdisplays_ndrvs", []):
                    display_id_str = display.get("_spdisplays_displayID", "")
                    # Convert hex display ID to decimal for Sunshine config
                    # macOS may return hex (e.g., "a" for 10)
                    try:
                        display_id = str(int(display_id_str, 16))
                    except ValueError:
                        # If it's not hex, use as-is (already decimal)
                        display_id = display_id_str

                    display_info = {
                        "name": display.get("_name", "Unknown"),
                        "id": display_id,
                        "resolution": display.get("_spdisplays_resolution", ""),
                        "pixels": display.get("_spdisplays_pixels", ""),
                        "is_main": display.get("spdisplays_main") == "spdisplays_yes",
                        "is_online": display.get("spdisplays_online") == "spdisplays_yes"
                    }
                    displays.append(display_info)

            if displays or attempt >= retries - 1:
                return displays

            # If no displays found, retry
            time.sleep(retry_delay)

        except subprocess.CalledProcessError as e:
            print(f"Error running system_profiler: {e}", file=sys.stderr)
            if attempt >= retries - 1:
                return []
            time.sleep(retry_delay)
        except subprocess.TimeoutExpired:
            print(f"system_profiler timed out (attempt {attempt + 1}/{retries})", file=sys.stderr)
            if attempt >= retries - 1:
                return []
            time.sleep(retry_delay)
        except json.JSONDecodeError as e:
            print(f"Error parsing system_profiler output: {e}", file=sys.stderr)
            if attempt >= retries - 1:
                return []
            time.sleep(retry_delay)

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


def get_current_sunshine_display():
    """Get the currently configured display ID from Sunshine."""
    config_path = get_sunshine_config_path()

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


def detect_sunshine_service():
    """Detect which sunshine service is installed and check if it's running."""
    try:
        result = subprocess.run(
            ["brew", "services", "list"],
            capture_output=True,
            text=True
        )
        lines = result.stdout.split('\n')
        for line in lines:
            if "sunshine-beta" in line:
                # Only "started" means running, everything else (stopped/none/error) means dead
                is_running = "started" in line
                return ("sunshine-beta", is_running)
            elif "sunshine" in line and "sunshine-beta" not in line:
                is_running = "started" in line
                return ("sunshine", is_running)
    except Exception:
        pass
    return (None, False)


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
    sunshine_service, is_running = detect_sunshine_service()

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

    # Try to start via launchctl kickstart (works even if already running)
    try:
        result = subprocess.run(["id", "-u"], capture_output=True, text=True)
        uid = result.stdout.strip()

        for service_name in ["homebrew.mxcl.sunshine-beta", "homebrew.mxcl.sunshine"]:
            result = subprocess.run(
                ["launchctl", "kickstart", f"gui/{uid}/{service_name}"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return True, f"Started via launchctl ({service_name})"
    except Exception:
        pass

    return False, "Could not start Sunshine"


def restart_sunshine():
    """Attempt to restart Sunshine service, forcing brew services restart."""
    # Detect which version is installed (sunshine or sunshine-beta)
    sunshine_service, is_running = detect_sunshine_service()

    # Always force restart via brew services
    if sunshine_service:
        try:
            # Always use restart, even if stopped - brew will handle it
            # Give it 60 seconds timeout as it can take a while
            result = subprocess.run(
                ["brew", "services", "restart", sunshine_service],
                capture_output=True,
                text=True,
                timeout=60
            )
            if result.returncode == 0:
                return True, f"Restarted via brew services ({sunshine_service})"

            # Log the error for debugging
            if result.stderr:
                print(f"brew services restart stderr: {result.stderr}", file=sys.stderr)

            # If restart failed, try stop then start
            subprocess.run(["brew", "services", "stop", sunshine_service],
                         capture_output=True, timeout=30)
            result = subprocess.run(
                ["brew", "services", "start", sunshine_service],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                return True, f"Force restarted via brew services ({sunshine_service})"

            if result.stderr:
                print(f"brew services start stderr: {result.stderr}", file=sys.stderr)

        except subprocess.TimeoutExpired:
            print(f"Warning: brew services timed out, trying fallback methods", file=sys.stderr)
        except FileNotFoundError:
            pass
        except Exception as e:
            print(f"Warning: brew services failed: {e}", file=sys.stderr)

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
        return True, "Force killed (service should auto-restart via launchd)"
    except Exception as e:
        return False, f"Could not restart: {e}"


def cmd_list(args):
    """List all available displays."""
    print("Available displays:")
    displays = get_displays()
    for display in displays:
        status = " (main)" if display["is_main"] else ""
        online = " [online]" if display["is_online"] else " [offline]"
        print(f"  - {display['name']}{status}{online}")
        print(f"    ID: {display['id']}, Resolution: {display['resolution']}")
    return 0


def cmd_update(args):
    """Update Sunshine configuration for a specific display."""
    display_name = args.display_name
    no_restart = args.no_restart

    # Find the display
    display = find_display_by_name(display_name)

    if not display:
        print(f"Error: Display '{display_name}' not found", file=sys.stderr)
        print("\nAvailable displays:", file=sys.stderr)
        displays = get_displays()
        for d in displays:
            print(f"  - {d['name']} (ID: {d['id']})", file=sys.stderr)
        return 1

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

    return 0


def cmd_watch(args):
    """Monitor mode - continuously watch and update when display changes."""
    import time

    config = load_config()
    if not config:
        print("Error: display_config.json not found!", file=sys.stderr)
        print("Please create it with your target display name.", file=sys.stderr)
        return 1

    target_display_name = config.get("target_display")
    if not target_display_name:
        print("Error: 'target_display' not specified in config", file=sys.stderr)
        return 1

    check_interval = config.get("check_interval_seconds", 60)
    no_restart = args.no_restart or config.get("no_auto_restart", False)
    daemon_mode = args.daemon

    if daemon_mode:
        # Force unbuffered output for logs
        sys.stdout.reconfigure(line_buffering=True)
        sys.stderr.reconfigure(line_buffering=True)

        print(f"Starting Sunshine Display Manager daemon")
        print(f"Target display: {target_display_name}")
        print(f"Check interval: {check_interval} seconds")
        print(f"Auto-restart: {'disabled' if no_restart else 'enabled'}")
        print()

    while True:
        try:
            # Ensure Sunshine is running
            success, message = ensure_sunshine_running()
            if not success:
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Warning: {message}", file=sys.stderr)
            elif "Started" in message:
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Sunshine was not running - {message}")

            # Find the display
            display = find_display_by_name(target_display_name)

            if not display:
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Warning: Display '{target_display_name}' not found", file=sys.stderr)
                time.sleep(check_interval)
                continue

            # Check if update is needed
            current_id = get_current_sunshine_display()
            if current_id != display['id']:
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Display ID changed: {current_id} -> {display['id']}")
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Updating configuration for {display['name']} (ID: {display['id']})")

                # Update Sunshine config
                config_path = update_sunshine_config(display['id'])
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Updated {config_path}")

                # Restart Sunshine if requested
                if not no_restart:
                    success, message = restart_sunshine()
                    if success:
                        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}")
                    else:
                        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Warning: {message}", file=sys.stderr)

            # Exit if not daemon mode, otherwise sleep until next check
            if not daemon_mode:
                return 0

            time.sleep(check_interval)

        except KeyboardInterrupt:
            print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Shutting down...")
            return 0
        except Exception as e:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Error: {e}", file=sys.stderr)
            if not daemon_mode:
                return 1
            time.sleep(check_interval)


def main():
    parser = argparse.ArgumentParser(
        description="Sunshine Display Manager - Manage display configuration for Sunshine"
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # List command
    list_parser = subparsers.add_parser('list', help='List all available displays')
    list_parser.set_defaults(func=cmd_list)

    # Update command
    update_parser = subparsers.add_parser('update', help='Update display configuration')
    update_parser.add_argument('display_name', help='Name of the display to use')
    update_parser.add_argument('--no-restart', action='store_true',
                               help='Do not restart Sunshine after update')
    update_parser.set_defaults(func=cmd_update)

    # Watch command (daemon mode)
    watch_parser = subparsers.add_parser('watch', help='Watch mode - check and update from config')
    watch_parser.add_argument('--no-restart', action='store_true',
                             help='Do not restart Sunshine after update')
    watch_parser.add_argument('--daemon', action='store_true',
                             help='Run continuously as a daemon')
    watch_parser.set_defaults(func=cmd_watch)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
