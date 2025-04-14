#!/bin/bash
# uninstall-node.sh
# This script uninstalls Node.js (and npm) that were installed system-wide using apt.

set -e

echo "Checking for Node.js installation..."

if command -v node >/dev/null 2>&1; then
    echo "Found Node.js version: $(node -v)"
else
    echo "Node.js is not installed system-wide."
    exit 0
fi

echo "Uninstalling Node.js and npm via apt..."
# Remove Node.js and purge configuration files
sudo apt-get remove -y nodejs npm
sudo apt-get purge -y nodejs npm
sudo apt-get autoremove -y

echo "Removing residual cache and config files..."
# Optionally remove user-specific npm and node folders (customize as needed)
rm -rf ~/.npm
rm -rf ~/.node-gyp

# Optional: If you have been using nvm and want to clean it up as well,
# uncomment the following line to remove its directory:
# rm -rf ~/.nvm

echo "Node.js uninstallation complete."
