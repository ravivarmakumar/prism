#!/bin/bash
# Setup script to install Node.js using nvm

echo "Setting up Node.js for podcast audio generation..."

# Load nvm
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

# Install Node.js LTS version
echo "Installing Node.js LTS..."
nvm install --lts

# Set as default
nvm alias default node

# Verify installation
echo ""
echo "Verifying installation..."
node --version
npm --version

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Node.js installed successfully!"
    echo ""
    echo "To use Node.js in your current terminal session, run:"
    echo "  export NVM_DIR=\"\$HOME/.nvm\""
    echo "  [ -s \"\$NVM_DIR/nvm.sh\" ] && \. \"\$NVM_DIR/nvm.sh\""
    echo ""
    echo "Or simply restart your terminal."
else
    echo "❌ Installation failed. Please check the error messages above."
fi
