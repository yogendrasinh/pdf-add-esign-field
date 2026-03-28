# Building Release Packages

Scripts and assets for producing distributable binaries using PyInstaller.

## Prerequisites (both platforms)

- A `.venv` must exist in the project root. Run the app at least once using `run.bat` (Windows) or `./run.sh` (macOS) to create the virtual environment and installs all dependencies automatically.
- `version.txt` contains the version string (e.g. `1.0`)

---

## Windows

Run from the project root:

```bat
package_gen\build_windows.bat
```

**Output:**
- `package_gen/dist/pdf-add-esign-field/` — the application folder, for developer test. Same folder ia available as zip (see below).
- `package_gen/pdf-add-esign-field_windows_v{VERSION}.zip` — the release archive for distribution. 

---

## macOS

### One-time setup: signing identity

Modify `package_gen/mac_info.ini` to add your distribution certificate name (issued by apple). The app becomes very difficult to use without signing the app so make all effort to use appropriate signing certificate.

> This repo is using distribution certificate of Cognirush Labs LLP and I am authorized to use that certificate to sign any app but it's not transferable. So, you find yours. 

```ini
[signing]
developer_id_application = Developer ID Application: Your Name (TEAMID)
```

To find your identity:

```bash
security find-identity -v -p codesigning
```

Also requires Xcode command-line tools and a valid Apple Developer ID certificate in Keychain.

### Run the build

```bash
package_gen/build_mac.sh
```

**Output:**
- `package_gen/dist/pdf-add-esign-field.app` — signed application bundle
- `package_gen/pdf-add-esign-field_mac_v{VERSION}.zip` — the release archive
