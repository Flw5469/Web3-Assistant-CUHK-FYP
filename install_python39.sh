#!/bin/bash
set -e

# Update package lists
echo "Updating package lists..."
sudo apt update

# Install prerequisites for adding PPAs
echo "Installing prerequisites..."
sudo apt install -y software-properties-common

# Add the deadsnakes PPA which contains Python 3.9
echo "Adding deadsnakes PPA..."
sudo add-apt-repository -y ppa:deadsnakes/ppa

# Update package lists again to include packages from the new PPA
sudo apt update

# Install Python 3.9, the venv module, and development headers
echo "Installing Python 3.9 and related packages..."
sudo apt install -y python3.9 python3.9-venv python3.9-dev

# Verify Python 3.9 installation
echo "Verifying Python 3.9 installation..."
python3.9 --version

# Create a virtual environment using Python 3.9 in the current directory named 'venv'
echo "Creating virtual environment..."
python3.9 -m venv venv

# Activate the virtual environment
echo "Activating virtual environment..."
# shellcheck source=/dev/null
source venv/bin/activate

# Upgrade pip in the virtual environment
echo "Upgrading pip..."
pip install --upgrade pip

# Install project dependencies from requirements.txt
# echo "Installing project dependencies..."
# pip install --break-system-packages -r requirements.txt

# echo "Installation complete. The virtual environment (venv) is active."
# echo "To activate it in the future, run: source venv/bin/activate" 