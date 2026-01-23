#!/bin/bash
# Script to install ffmpeg for podcast audio generation

echo "Installing ffmpeg for podcast audio generation..."

# Check if Homebrew is available
if command -v brew &> /dev/null; then
    echo "Installing ffmpeg using Homebrew..."
    brew install ffmpeg
    if [ $? -eq 0 ]; then
        echo "✅ ffmpeg installed successfully!"
        echo ""
        echo "You can now generate podcasts with audio."
    else
        echo "❌ Failed to install ffmpeg via Homebrew."
        echo "Please install manually from: https://ffmpeg.org/download.html"
    fi
elif command -v apt-get &> /dev/null; then
    echo "Installing ffmpeg using apt-get..."
    sudo apt-get update
    sudo apt-get install -y ffmpeg
    if [ $? -eq 0 ]; then
        echo "✅ ffmpeg installed successfully!"
    else
        echo "❌ Failed to install ffmpeg via apt-get."
    fi
elif command -v yum &> /dev/null; then
    echo "Installing ffmpeg using yum..."
    sudo yum install -y ffmpeg
    if [ $? -eq 0 ]; then
        echo "✅ ffmpeg installed successfully!"
    else
        echo "❌ Failed to install ffmpeg via yum."
    fi
else
    echo "❌ No package manager found (brew, apt-get, or yum)."
    echo ""
    echo "Please install ffmpeg manually:"
    echo "  macOS: Download from https://evermeet.cx/ffmpeg/ or use Homebrew"
    echo "  Linux: Use your distribution's package manager"
    echo "  Windows: Download from https://ffmpeg.org/download.html"
    echo ""
    echo "Or visit: https://ffmpeg.org/download.html"
fi
