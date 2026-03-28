# Developer Notes

Technical notes for contributors and anyone running the app from source.

## Project structure

```
pdf-add-esign-field/
├── source/
│   ├── app.py              # Main application (tkinter GUI)
│   └── requirements.txt    # Python dependencies
├── package_gen/            # Build scripts and packaging assets
│   ├── build_windows.bat
│   ├── build_mac.sh
│   ├── pdf-add-esign-field.spec  # PyInstaller spec
│   └── version.txt
├── run.bat                 # Windows launcher (creates .venv, runs app)
└── run.sh                  # macOS/Linux launcher (creates .venv, runs app)
```

## Dependencies

| Package | Purpose |
|---------|---------|
| `pyHanko` | Embeds signature fields into PDFs |
| `PyMuPDF` | Renders PDF pages to images for the preview |
| `Pillow` | Image handling for the tkinter canvas |
| `tkinterdnd2` | Optional drag-and-drop support (app works without it) |

Install with:

```bash
pip install -r source/requirements.txt
```

## Launcher scripts

`run.bat` (Windows) and `run.sh` (macOS/Linux) both:

1. Look for an existing `.venv` in the project root
2. Create one if it doesn't exist, installing all dependencies
3. Launch `source/app.py`

### macOS: Python and Tk requirements

The app requires Python 3 with Tk **8.6 or newer**. The Xcode-bundled `/usr/bin/python3` ships with Tk 8.5 and will not work correctly so avoid it.

`run.sh` attempts to auto-select a suitable Python before creating `.venv`. If it fails with:

```text
ModuleNotFoundError: No module named '_tkinter'
```

install the matching Tk package for your Python version. For example, for Python 3.14:

```bash
brew install python-tk@3.14
./run.sh
```

To point the launcher at a specific Python interpreter:

```bash
PYTHON_BIN=/opt/homebrew/bin/python3.14 ./run.sh
```

### macOS: drag-and-drop

The optional `tkinterdnd2` drag-and-drop extension may not load on macOS. The app falls back gracefully to the standard Tk window (i.e. the `Browse` button that still works normally). 

> Note: drag-and-drop onto the window is currently not working on Mac (known issue).

## Use of AI

Use of AI is permitted by contributors. Non-negotiable condition for contributors: Code must be reviewed and software must be tested on Mac and Windows by the contributor themselves. 

## Building distributable binaries

See [package_gen/README.md](package_gen/README.md) for instructions on producing the Windows and macOS release packages.
