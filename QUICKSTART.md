# Quick Start Guide

## Setup (2 minutes)

1. **Check your current display setup:**
   ```bash
   ./update_sunshine_display.py list
   ```

   This will show you all available displays. Note the name of the display you want to use.

2. **Edit the config file:**

   The `display_config.json` is already set to use "Virtual 16:9". If you want a different display, edit it:
   ```json
   {
     "target_display": "Your Display Name Here"
   }
   ```

3. **Install the automatic updater:**
   ```bash
   ./install.sh
   ```

That's it! The system will now automatically update Sunshine whenever your display ID changes.

## What Just Happened?

- A background service (launchd agent) now runs every 60 seconds
- It checks if your target display's ID has changed
- If changed, it updates `~/.config/sunshine/sunshine.conf` automatically
- Sunshine is restarted to apply the change

## Testing

To test the manual update:
```bash
./update_sunshine_display.py update "Virtual 16:9"
```

To see the auto-updater in action:
```bash
./update_sunshine_display.py watch
```

## Logs

Watch for updates in real-time:
```bash
tail -f update.log
```

## Uninstall

```bash
./uninstall.sh
```

## Troubleshooting

**Problem**: Display not found
- Run `./update_sunshine_display.py list` to see exact display names
- The name matching is case-insensitive and supports partial matches

**Problem**: Sunshine not restarting automatically
- Add `"no_auto_restart": true` to `display_config.json`
- Restart Sunshine manually when needed

**Problem**: Service not running
- Check: `launchctl list | grep sunshine`
- Reinstall: `./uninstall.sh` then `./install.sh`
