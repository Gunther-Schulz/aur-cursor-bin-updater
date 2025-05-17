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
- `cursor-bin.sh` - Launch script

## Development Notes

- Build artifacts and downloaded files are ignored via `.gitignore`
- The scripts check both ToDesktop and direct S3 URLs for updates
- Version checks include both stable and preview channels

## Troubleshooting

### Common Issues

1. **Build fails with checksum mismatch**:

   ```bash
   # Regenerate checksums
   updpkgsums
   ```

2. **Package won't install**:

   ```bash
   # Check dependencies
   pacman -Syu fuse2 gtk3
   ```

3. **Cursor won't launch**:
   ```bash
   # Check if FUSE is running
   systemctl status systemd-fusectl
   ```

### Debug Mode

Run the check script in debug mode for more information:

```bash
DEBUG=true python check.py
```
