#!/bin/bash

set -e

### Configuration ###

REPO_URL="https://github.com/exodialabsxyz/exodus.git"
INSTALL_DIR="$HOME/.exodus"

echo "--- Starting EXODUS Installation ---"

### Detect Debian based systems ###
if [ -f /etc/debian_version]; then
    echo "Detected Debian based system"
    echo "Installing Basedependencies..."
    sudo apt-get update && sudo apt-get install -y git python3 python3-pip python3-venv
else
    echo "Unsupported system. Only Debian based systems are supported."
    exit 1
fi

### Cloning or updating the repository ###
if [ -d "$INSTALL_DIR" ]; then
    echo "Updating existing EXODUS installation..."
    cd "$INSTALL_DIR"
    git pull
else
    echo "Cloning EXODUS repository..."
    git clone --depth 1 "$REPO_URL" "$INSTALL_DIR"
fi

### Executing the python installer ###
echo "Executing python installer..."
cd "$INSTALL_DIR"
python3 exodus/install/setup.py