#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
APP_NAME="pdf-add-esign-field"
APP_BUNDLE_NAME="${APP_NAME}.app"
ENTRY_POINT="$PROJECT_ROOT/source/app.py"
VENV_PYTHON="$PROJECT_ROOT/.venv/bin/python3"
VENV_PIP="$PROJECT_ROOT/.venv/bin/pip"
CONFIG_PATH="$SCRIPT_DIR/mac_info.ini"
ICON_ICO_PATH="$SCRIPT_DIR/${APP_NAME}.ico"
ICON_ICNS_PATH="$SCRIPT_DIR/${APP_NAME}.icns"

VERSION="$(cat "$SCRIPT_DIR/version.txt" | tr -d '[:space:]')"

read_ini_value() {
    local section="$1"
    local key="$2"
    local file_path="$3"

    awk -F '=' -v target_section="$section" -v target_key="$key" '
        /^[[:space:]]*\[/ {
            in_section = ($0 ~ "^[[:space:]]*\\[" target_section "\\][[:space:]]*$")
            next
        }
        in_section {
            current_key = $1
            sub(/^[[:space:]]+/, "", current_key)
            sub(/[[:space:]]+$/, "", current_key)
            if (current_key == target_key) {
                value = substr($0, index($0, "=") + 1)
                sub(/^[[:space:]]+/, "", value)
                sub(/[[:space:]]+$/, "", value)
                gsub(/^"|"$/, "", value)
                print value
                exit
            }
        }
    ' "$file_path"
}

if [ ! -f "$CONFIG_PATH" ]; then
    echo "ERROR: Missing config file: $CONFIG_PATH"
    exit 1
fi

SIGNING_IDENTITY="$(read_ini_value "signing" "developer_id_application" "$CONFIG_PATH")"
if [ -z "$SIGNING_IDENTITY" ]; then
    echo "ERROR: 'developer_id_application' is missing in $CONFIG_PATH"
    exit 1
fi

if [ ! -f "$ICON_ICO_PATH" ]; then
    echo "ERROR: Missing icon file: $ICON_ICO_PATH"
    exit 1
fi

echo "[build] App:     $APP_NAME"
echo "[build] Version: $VERSION"
echo "[build] Entry:   $ENTRY_POINT"
echo "[build] Config:  $CONFIG_PATH"
echo "[build] Sign ID: $SIGNING_IDENTITY"
echo "[build] Icon:    $ICON_ICO_PATH"

if [ ! -f "$VENV_PYTHON" ]; then
    echo "ERROR: .venv not found. Run ./run.sh first to create the virtual environment."
    exit 1
fi

echo "[build] Checking PyInstaller..."
if ! "$VENV_PYTHON" -m PyInstaller --version >/dev/null 2>&1; then
    echo "[build] Installing PyInstaller..."
    "$VENV_PIP" install pyinstaller
fi

if ! command -v codesign >/dev/null 2>&1; then
    echo "ERROR: codesign is not available on this Mac."
    exit 1
fi

echo "[build] Generating macOS .icns icon..."
"$VENV_PYTHON" - <<PY
from PIL import Image

src = Image.open(r"$ICON_ICO_PATH")
src.save(
    r"$ICON_ICNS_PATH",
    format="ICNS",
    sizes=[(16, 16), (32, 32), (64, 64), (128, 128), (256, 256), (512, 512)],
)
PY

cd "$SCRIPT_DIR"

"$VENV_PYTHON" -m PyInstaller \
    --noconfirm \
    --onedir \
    --windowed \
    --name "$APP_NAME" \
    --icon "$ICON_ICNS_PATH" \
    --collect-all pyhanko \
    --collect-all pyhanko_certvalidator \
    --collect-all pymupdf \
    --hidden-import fitz \
    --hidden-import PIL._tkinter_finder \
    "$ENTRY_POINT"

APP_BUNDLE_PATH="$SCRIPT_DIR/dist/$APP_BUNDLE_NAME"
ZIP_NAME="${APP_NAME}_mac_v${VERSION}.zip"
ZIP_PATH="$SCRIPT_DIR/$ZIP_NAME"

if [ ! -d "$APP_BUNDLE_PATH" ]; then
    echo "ERROR: PyInstaller did not produce $APP_BUNDLE_PATH"
    exit 1
fi

echo "[build] Signing app bundle..."
codesign --force --deep --options runtime --timestamp \
    --sign "$SIGNING_IDENTITY" \
    "$APP_BUNDLE_PATH"

echo "[build] Verifying signature..."
codesign --verify --deep --strict --verbose=2 "$APP_BUNDLE_PATH"

rm -f "$ZIP_PATH"

echo "[build] Creating $ZIP_NAME..."
ditto -c -k --keepParent "$APP_BUNDLE_PATH" "$ZIP_PATH"

echo ""
echo "[build] SUCCESS: $ZIP_PATH"
