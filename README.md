# aur-cursor-bin-updater

Automated updater for the [cursor-bin](https://aur.archlinux.org/packages/cursor-bin) AUR package. This repository helps maintain the Cursor IDE binary package for Arch Linux.

## Usage

### Installing Cursor IDE

If you just want to install Cursor IDE on Arch Linux, use your preferred AUR helper:

```bash
# Using yay
yay -S cursor-bin

# Using paru
paru -S cursor-bin
```

### Maintaining/Contributing

1. **Clone the repository**:

   ```bash
   git clone https://github.com/yourusername/aur-cursor-bin-updater.git
   cd aur-cursor-bin-updater
   ```

2. **Check for updates**:

   ```bash
   python check.py
   ```

   This will create a `check_output.json` file with update information.

3. **Apply updates**:

   ```bash
   python update_pkgbuild.py check_output.json
   ```

   This updates the PKGBUILD with new version, URL, and checksums.

4. **Test the package**:

   ```bash
   # Build and install
   makepkg -si

   # Just build without installing
   makepkg -s
   ```

5. **Submit changes**:
   - Update the AUR package using your preferred method (manual or aurpublish)
   - Create a PR to this repository if you've made improvements to the scripts

## Repository Structure

- `PKGBUILD` - The main package build script
- `check.py` - Script to check for new Cursor versions
- `update_pkgbuild.py` - Script to update PKGBUILD automatically
- `README.md` - This documentation file

## Development Notes

- Build artifacts and downloaded files are ignored via `.gitignore`
- The scripts check the official Cursor API for updates
- Version checks are performed against the stable release channel
- The `update_pkgbuild.py` script automatically determines the correct Electron version from VSCode's package-lock.json
- The script generates a `cursor.sh` launch script by transforming Arch Linux's `code.sh` template

## Troubleshooting

### Common Issues

1. **Build fails with checksum mismatch**:
   - The script automatically calculates and updates checksums
   - If manual intervention is needed, regenerate checksums:
   ```bash
   updpkgsums
   ```

2. **Package won't install**:
   - Check dependencies:
   ```bash
   pacman -Syu ripgrep xdg-utils gcc-libs hicolor-icon-theme libxkbfile electron28
   ```

3. **Cursor won't launch**:
   - Ensure the `cursor.sh` script was generated:
   ```bash
   ls -la cursor.sh
   ```
   - Check if the script is executable:
   ```bash
   chmod +x cursor.sh
   ```

4. **Update script fails**:
   - Run in debug mode for detailed information:
   ```bash
   DEBUG=true python check.py
   DEBUG=true python update_pkgbuild.py check_output.json
   ```

### Debug Mode

Run the scripts in debug mode for more information:

```bash
DEBUG=true python check.py
DEBUG=true python update_pkgbuild.py check_output.json
```

### Verification Features

The update script includes comprehensive verification to ensure updates are applied correctly:

- **Change tracking**: Monitors which specific PKGBUILD values were updated
- **Content validation**: Verifies all expected values are present after updates
- **File integrity**: Confirms files are written successfully to disk
- **Error handling**: Provides clear error messages and stops on critical failures
- **Automatic cleanup**: Removes temporary files and handles exceptions gracefully
