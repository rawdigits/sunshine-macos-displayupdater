#!/bin/bash
# Installation script for Sunshine Display Updater

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PLIST_NAME="com.sunshine.displayupdater.plist"
PLIST_TEMPLATE="$SCRIPT_DIR/example/$PLIST_NAME"
PLIST_DEST="$HOME/Library/LaunchAgents/$PLIST_NAME"

echo "Sunshine Display Updater - Installation"
echo "========================================"
echo

# Check if config exists
if [ ! -f "$SCRIPT_DIR/display_config.json" ]; then
    echo "Error: display_config.json not found!"
    echo "Please create it with your target display name."
    echo
    echo "Example:"
    echo '  {"target_display": "Virtual 16:9"}'
    exit 1
fi

# Test the script
echo "Testing configuration..."
if ! python3 "$SCRIPT_DIR/update_sunshine_display.py" watch --no-restart; then
    echo
    echo "Error: Script test failed. Please check your configuration."
    exit 1
fi

echo
echo "Configuration test successful!"
echo

# Install launchd agent
echo "Installing launchd agent..."

# Create LaunchAgents directory if it doesn't exist
mkdir -p "$HOME/Library/LaunchAgents"

# Generate plist file with actual paths
sed "s|INSTALL_DIR|$SCRIPT_DIR|g" "$PLIST_TEMPLATE" > "$PLIST_DEST"
echo "  Created plist at $PLIST_DEST"

# Unload if already loaded
launchctl unload "$PLIST_DEST" 2>/dev/null || true

# Load the agent
launchctl load "$PLIST_DEST"
echo "  Loaded launchd agent"

# Apply the current configuration with restart
echo
echo "Applying configuration and restarting Sunshine..."
# Get the target display from config
TARGET_DISPLAY=$(python3 -c "import json; print(json.load(open('$SCRIPT_DIR/display_config.json'))['target_display'])")
# Use the update command to force a restart
if python3 "$SCRIPT_DIR/update_sunshine_display.py" update "$TARGET_DISPLAY"; then
    echo "  Configuration applied successfully"
else
    echo "  Warning: Could not apply configuration automatically"
    echo "  You may need to restart Sunshine manually"
fi

echo
echo "Installation complete!"
echo
echo "The display updater will now run:"
echo "  - Every 60 seconds"
echo "  - At system boot"
echo
echo "Logs are saved to:"
echo "  - $SCRIPT_DIR/update.log"
echo "  - $SCRIPT_DIR/update.error.log"
echo
echo "To uninstall, run:"
echo "  ./uninstall.sh"
