#!/bin/bash
echo "--- Uninstalling EXODUS ---"

# Delete binaries
rm -f ~/.local/bin/exodus-cli ~/.local/bin/exodus-server ~/.local/bin/exodus-server-exec

# Ask if you want to delete the configuration (in case you want to reinstall later)
read -p "Do you want to delete your configuration and API Keys in ~/.exodus? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    rm -rf ~/.exodus
fi

echo "Uninstallation completed."