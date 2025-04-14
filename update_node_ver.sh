#!/bin/bash
# update_node_ver.sh
# This script installs nvm (if not already installed) and updates Node.js to the latest LTS version.

# Function to load nvm into the current shell session.
load_nvm() {
  export NVM_DIR="$HOME/.nvm"
  if [ -s "$NVM_DIR/nvm.sh" ]; then
    . "$NVM_DIR/nvm.sh"
  else
    echo "Error: nvm script not found in $NVM_DIR/nvm.sh"
    exit 1
  fi
}

# Check if nvm is installed
if command -v nvm >/dev/null 2>&1; then
  echo "nvm is already installed."
else
  echo "nvm is not installed. Installing nvm..."
  # Download and install nvm (latest stable version)
  curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.3/install.sh | bash
  
  # Load nvm into the current shell session
  load_nvm
fi

# Ensure nvm is loaded (this works if nvm was pre-installed as well)
load_nvm

# Install the latest LTS version of Node.js
echo "Installing the latest LTS version of Node.js..."
nvm install --lts

# Use the newly installed LTS version
nvm use --lts

# Verify and display the Node.js version
echo "Node.js version updated to: $(node -v)"

# Remind the user to source .bashrc
echo "To use the updated Node.js version in this terminal, run: source ~/.bashrc"
echo "Alternatively, open a new terminal to start using the updated version."