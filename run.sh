#!/bin/bash
# Note: First-time setup on Mac/Linux requires making this script executable.
# Open a terminal in this folder and run: chmod +x run.sh
# After that, you can run it with: ./run.sh

# Check if python3 is installed
if ! command -v python3 &>/dev/null; then
    echo "Python 3 is not installed on this system."
    echo ""
    # Detect OS and give platform-specific instructions
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "On macOS, install Python with Homebrew:"
        echo "  brew install python3"
        echo ""
        echo "If you don't have Homebrew, install it first from https://brew.sh"
    else
        echo "On Ubuntu/Debian, install Python with:"
        echo "  sudo apt install python3 python3-venv"
        echo ""
        echo "On Fedora/RHEL:"
        echo "  sudo dnf install python3"
    fi
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
    if [ $? -ne 0 ]; then
        echo "Failed to create virtual environment."
        echo "On some systems you may need to install python3-venv:"
        echo "  sudo apt install python3-venv"
        exit 1
    fi
fi

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r source/requirements.txt
if [ $? -ne 0 ]; then
    echo "Failed to install dependencies."
    exit 1
fi

# Run the app
echo "Starting app..."
python source/app.py
