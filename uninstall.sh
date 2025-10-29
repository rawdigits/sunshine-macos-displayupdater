#!/bin/bash
# Uninstallation script for Sunshine Display Updater

PLIST_NAME="com.sunshine.displayupdater.plist"
PLIST_DEST="$HOME/Library/LaunchAgents/$PLIST_NAME"

echo "Sunshine Display Updater - Uninstallation"
echo "=========================================="
echo

if [ -f "$PLIST_DEST" ]; then
    echo "Unloading launchd agent..."
    launchctl unload "$PLIST_DEST" 2>/dev/null || true

    echo "Removing plist file..."
    rm "$PLIST_DEST"

    echo
    echo "Uninstallation complete!"
else
    echo "LaunchAgent not found. Nothing to uninstall."
fi
