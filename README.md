# pdf-add-esign-field
Add blank E-Signature Fields to a PDF

## Run

### macOS

This app uses `tkinter` for its desktop UI. If `./run.sh` fails with:

```text
ModuleNotFoundError: No module named '_tkinter'
```

your Python build either does not include Tk support, or it is linked against an old Tk runtime that cannot open a GUI window on current macOS.

`./run.sh` now tries to auto-select a Python that can actually create a Tk GUI window on macOS before creating `.venv`.

If the optional `tkinterdnd2` drag-and-drop extension cannot load on macOS, the app now falls back to the standard Tk window and still works through the `Browse` button.

If no installed Python on your Mac has Tk support, install the matching Tk package for the Python version you want to use. For example, if `python3 --version` shows `3.14.x`:

```bash
brew install python-tk@3.14
./run.sh
```

Avoid relying on the Xcode-provided `/usr/bin/python3` for this app; on this machine it reports Tk `8.5`, which is too old.

You can also point the launcher at another Python interpreter that has a working Tk `8.6+` GUI runtime:

```bash
PYTHON_BIN=/opt/homebrew/bin/python3.14 ./run.sh
```
