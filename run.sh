#!/bin/bash
# Note: First-time setup on Mac/Linux requires making this script executable.
# Open a terminal in this folder and run: chmod +x run.sh
# After that, you can run it with: ./run.sh

# Allow callers to override the interpreter, e.g.
#   PYTHON_BIN=/opt/homebrew/bin/python3.14 ./run.sh
PYTHON_BIN_WAS_SET=0
if [ -n "${PYTHON_BIN:-}" ]; then
    PYTHON_BIN_WAS_SET=1
fi
PYTHON_BIN="${PYTHON_BIN:-python3}"

python_tk_version() {
    local py_bin="$1"
    "$py_bin" -c "import tkinter as tk; print(tk.TkVersion)" 2>/dev/null || true
}

python_supports_tk_gui() {
    local py_bin="$1"
    "$py_bin" - <<'PY' >/dev/null 2>&1
import tkinter as tk

if tk.TkVersion < 8.6:
    raise SystemExit(1)

root = tk.Tk()
root.withdraw()
root.update_idletasks()
root.destroy()
PY
}

append_unique_python_candidate() {
    local candidate="$1"

    if [ -z "$candidate" ]; then
        return
    fi

    for existing in "${PYTHON_CANDIDATES[@]}"; do
        if [ "$existing" = "$candidate" ]; then
            return
        fi
    done

    PYTHON_CANDIDATES+=("$candidate")
}

resolve_python_candidate() {
    local candidate="$1"

    if [ -x "$candidate" ]; then
        echo "$candidate"
        return
    fi

    command -v "$candidate" 2>/dev/null || true
}

select_macos_python_bin() {
    local candidate=""
    local resolved=""

    PYTHON_CANDIDATES=()

    append_unique_python_candidate "$(resolve_python_candidate "$PYTHON_BIN")"
    append_unique_python_candidate "$(resolve_python_candidate "python3")"

    for candidate in python3.14 python3.13 python3.12 python3.11 python3.10 python3.9; do
        resolved="$(resolve_python_candidate "$candidate")"
        append_unique_python_candidate "$resolved"
    done

    append_unique_python_candidate "/usr/bin/python3"

    for candidate in "${PYTHON_CANDIDATES[@]}"; do
        if python_supports_tk_gui "$candidate"; then
            echo "$candidate"
            return 0
        fi
    done

    return 1
}

print_macos_tk_help() {
    local py_executable="$1"
    local py_version="$2"
    local tk_version="$3"

    echo "This Python interpreter cannot start a Tk GUI window, which this desktop app needs."
    echo "Interpreter: $py_executable"
    echo "Version:     $py_version"
    if [ -n "$tk_version" ]; then
        echo "Tk version:  $tk_version"
    fi
    echo ""

    if command -v brew &>/dev/null; then
        echo "If you are using Homebrew Python, install the matching Tk package for that Python version:"
        echo "  brew install python-tk@$py_version"
        echo ""
    fi

    echo "The Xcode-provided /usr/bin/python3 on this Mac exposes Tk 8.5, which is too old for this app on current macOS."
    echo ""
    echo "Then rerun:"
    echo "  ./run.sh"
    echo ""
    echo "You can also point the launcher at another interpreter with a working Tk 8.6+ GUI runtime:"
    echo "  PYTHON_BIN=/opt/homebrew/bin/python3.14 ./run.sh"
}

# Check if the selected Python is installed
if ! command -v "$PYTHON_BIN" &>/dev/null; then
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

if [[ "$OSTYPE" == "darwin"* ]] && [ "$PYTHON_BIN_WAS_SET" -eq 0 ]; then
    SELECTED_PYTHON_BIN="$(select_macos_python_bin)"
    if [ -n "$SELECTED_PYTHON_BIN" ]; then
        PYTHON_BIN="$SELECTED_PYTHON_BIN"
    fi
fi

PYTHON_EXECUTABLE="$("$PYTHON_BIN" -c 'import sys; print(sys.executable)')"
PYTHON_VERSION="$("$PYTHON_BIN" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
PYTHON_TK_VERSION="$(python_tk_version "$PYTHON_BIN")"

if [[ "$OSTYPE" == "darwin"* ]]; then
    if ! python_supports_tk_gui "$PYTHON_BIN"; then
        print_macos_tk_help "$PYTHON_EXECUTABLE" "$PYTHON_VERSION" "$PYTHON_TK_VERSION"
        exit 1
    fi
fi

if [ -d ".venv" ] && [ ! -x ".venv/bin/python" ]; then
    echo "Existing virtual environment is incomplete. Recreating it..."
    rm -rf .venv
fi

if [ -d ".venv" ] && [[ "$OSTYPE" == "darwin"* ]]; then
    if ! python_supports_tk_gui ".venv/bin/python"; then
        VENV_TK_VERSION="$(python_tk_version ".venv/bin/python")"
        echo "Existing virtual environment does not have a working Tk GUI runtime."
        if [ -n "$VENV_TK_VERSION" ]; then
            echo "Current .venv Tk version: $VENV_TK_VERSION"
        fi
        echo "Recreating .venv with: $PYTHON_EXECUTABLE"
        rm -rf .venv
    fi
fi

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    echo "Using Python: $PYTHON_EXECUTABLE"
    "$PYTHON_BIN" -m venv .venv
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
