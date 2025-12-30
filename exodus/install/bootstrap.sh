#!/bin/bash

set -e

### Configuration ###

REPO_URL="https://github.com/exodialabsxyz/exodus.git"
INSTALL_DIR="$HOME/.exodus"

echo "--- Starting EXODUS Installation ---"

### Detect Debian based systems ###
if command -v apt >/dev/null 2>&1; then
    echo "APT package manager detected (Debian-based system)."
    echo "Installing base dependencies..."
    sudo apt-get update && sudo apt install -y git python3 python3-pip python3-venv
elif command -v dnf >/dev/null 2>&1; then
    echo "Detected RPM based system (dnf)."
    echo "Please install base dependencies manually: git python3 python3-pip python3-venv"
    read -p "Once installed, press Enter to continue the installation..."
elif command -v pacman >/dev/null 2>&1; then
    echo "Detected Arch based system (pacman)."
    echo "Please install base dependencies manually: git python python-pip"
    read -p "Once installed, press Enter to continue the installation..."
elif [[ "$(uname -s)" == "Darwin" ]]; then
    echo "macOS detected."
    if ! command -v brew >/dev/null 2>&1; then
        echo "Homebrew is not installed. Please install Homebrew first"
        read -p "Once Homebrew is installed, press Enter to continue the installation..."
    fi
    echo "Installing base dependencies with Homebrew..."
    brew install git python3
else
    echo "Error: This installer requires a supported package manager (APT, DNF, Pacman) or macOS."
    echo "If you are on an unsupported system, please install dependencies manually."
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