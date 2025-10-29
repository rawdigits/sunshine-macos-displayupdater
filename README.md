# Sunshine Display Updater

Automatically keeps Sunshine's display configuration up-to-date on macOS when display IDs change.

## Problem

On macOS, Sunshine requires you to specify a display ID in its configuration (`output_name`). However, these IDs can change:
- After system reboots
- When plugging/unplugging monitors
- When display configurations change

This tool automatically detects your target display by name and updates Sunshine's configuration with the current display ID.

## Features

- **Display matching by name**: Specify your display by its friendly name (e.g., "Virtual 16:9")
- **Automatic monitoring**: Runs every 60 seconds to check for display ID changes
- **Smart updates**: Only updates configuration and restarts Sunshine when the ID actually changes
- **Boot-time execution**: Runs automatically when you log in
- **Logging**: Keeps logs of all updates for troubleshooting

## Installation

### 1. Configure your target display

Edit `display_config.json` to specify which display you want Sunshine to use:

```json
{
  "target_display": "Virtual 16:9"
}
```

To see available display names, run:

```bash
./update_sunshine_display.py
```

### 2. Run the installer

```bash
./install.sh
```

This will:
- Test your configuration
- Install a launchd agent that runs automatically
- Start monitoring immediately

## Usage

### Manual Update

To manually update Sunshine's display configuration:

```bash
./update_sunshine_display.py "Virtual 16:9"
```

Options:
- `--no-restart`: Don't restart Sunshine after updating

### Check Current Status

View the auto-update logs:

```bash
tail -f update.log
```

View any errors:

```bash
tail -f update.error.log
```

### List Available Displays

```bash
./update_sunshine_display.py
```

This will show all connected displays with their names, IDs, and resolutions.

## How It Works

1. **Display Detection**: Uses `system_profiler SPDisplaysDataType` to get all connected displays
2. **Name Matching**: Finds your target display by name (supports partial matching)
3. **Configuration Update**: Updates `~/.config/sunshine/sunshine.conf` with the correct `output_name`
4. **Sunshine Restart**: Automatically restarts Sunshine to apply changes

## Configuration Options

Edit `display_config.json`:

```json
{
  "target_display": "Virtual 16:9",
  "no_auto_restart": false
}
```

- `target_display`: The name of the display to use (required)
- `no_auto_restart`: Set to `true` to skip automatic Sunshine restarts

## Automatic Monitoring

The launchd agent runs:
- Every 60 seconds (configurable in the plist file)
- At login/boot time
- In the background

To modify the check interval, edit `com.sunshine.displayupdater.plist` and change the `StartInterval` value (in seconds).

## Files

- `update_sunshine_display.py`: Manual update script
- `auto_update_sunshine_display.py`: Automatic update script (used by launchd)
- `display_config.json`: Configuration file
- `com.sunshine.displayupdater.plist`: launchd agent definition
- `install.sh`: Installation script
- `uninstall.sh`: Uninstallation script

## Troubleshooting

### Check if the agent is running

```bash
launchctl list | grep sunshine
```

You should see `com.sunshine.displayupdater` in the list.

### Manually run the auto-update script

```bash
./auto_update_sunshine_display.py
```

### View logs

```bash
# Standard output
cat update.log

# Errors
cat update.error.log
```

### Display not found

Make sure your display name matches exactly. Run `./update_sunshine_display.py` to see all available displays.

The script supports partial matching, so "Virtual" would match "Virtual 16:9".

### Sunshine not restarting

The script tries two methods to restart Sunshine:
1. `brew services restart sunshine` (if installed via Homebrew)
2. `pkill -x sunshine` (kills the process)

You can disable auto-restart by adding `"no_auto_restart": true` to `display_config.json`.

## Uninstallation

```bash
./uninstall.sh
```

This will stop and remove the launchd agent. Your configuration files remain intact.

## Advanced Usage

### Different check intervals

Edit the plist file and change `StartInterval`:

```xml
<key>StartInterval</key>
<integer>300</integer>  <!-- Check every 5 minutes -->
```

Then reload the agent:

```bash
launchctl unload ~/Library/LaunchAgents/com.sunshine.displayupdater.plist
launchctl load ~/Library/LaunchAgents/com.sunshine.displayupdater.plist
```

### Run on display change events only

Instead of periodic checking, you could modify the plist to use `WatchPaths`:

```xml
<key>WatchPaths</key>
<array>
    <string>/tmp/display-change-trigger</string>
</array>
```

Then trigger updates by touching that file when needed.

## Requirements

- macOS
- Python 3 (included with macOS)
- Sunshine installed and configured

## License

Free to use and modify as needed.
