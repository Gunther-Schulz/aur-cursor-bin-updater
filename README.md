# AUR Cursor Binary Package Updater

Automated maintenance system for the [cursor-bin](https://aur.archlinux.org/packages/cursor-bin) AUR package. This repository automatically monitors Cursor IDE releases and maintains the PKGBUILD for Arch Linux users.

## 🎯 What This Repository Does

This is **not** a manual installation guide for Cursor IDE. Instead, it's an automated system that:

- 🔍 **Monitors** Cursor IDE releases automatically via GitHub Actions
- 📦 **Generates** proper PKGBUILDs with correct versions, checksums, and dependencies  
- 🚀 **Publishes** updates to the AUR automatically
- ✅ **Validates** all changes with comprehensive testing (25+ checks)
- 🔧 **Maintains** the package using modern .deb format (not AppImage)

## 📥 Installing Cursor IDE (End Users)

If you just want to **install** Cursor IDE on Arch Linux, use your AUR helper:

```bash
# Using yay
yay -S cursor-bin

# Using paru  
paru -S cursor-bin

# Using makepkg (manual)
git clone https://aur.archlinux.org/cursor-bin.git
cd cursor-bin
makepkg -si
```

## 🛠️ Development & Maintenance

### Architecture Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Cursor.com    │───▶│  GitHub Actions  │───▶│  AUR Package    │
│   (releases)    │    │  (this repo)     │    │  (cursor-bin)   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌──────────────────┐
                       │   Validation     │
                       │   (25+ checks)   │
                       └──────────────────┘
```

### Key Components

| File | Purpose |
|------|---------|
| `check.py` | Detects new Cursor releases and determines update necessity |
| `update_pkgbuild.py` | Updates PKGBUILD with new versions, URLs, and checksums |
| `validate_pkgbuild.py` | Comprehensive validation (25+ checks) of generated PKGBUILD |
| `test_workflow.py` | Local testing framework for the entire workflow |
| `.github/workflows/update-aur.yml` | Automated GitHub Actions workflow |
| `PKGBUILD` | The actual package build script |

### Automated Workflow

1. **🕐 Scheduled Check**: GitHub Actions runs daily (and on manual trigger)
2. **🔍 Version Detection**: `check.py` compares latest Cursor version with AUR
3. **📦 PKGBUILD Update**: `update_pkgbuild.py` generates new PKGBUILD with:
   - Correct version and commit hash
   - Updated download URLs  
   - Recalculated SHA512 checksums
   - Dynamic Electron version detection
4. **✅ Validation**: 25+ comprehensive checks ensure quality *(development branch only)*
5. **🚀 AUR Publish**: Automatic commit and push to AUR *(main branch only)*

**Branch Behavior**:
- **Development**: Runs steps 1-4, skips AUR publish for safe testing
- **Main**: Runs steps 1-3 + 5, skips validation for faster production updates

### Local Development

#### Prerequisites

```bash
# Install required tools
sudo pacman -S python python-requests bsdtar
pip install requests

# For local testing (optional)
yay -S act-bin  # GitHub Actions local runner
```

#### Manual Update Process

```bash
# 1. Check for updates
python check.py

# 2. Apply updates (if needed)
python update_pkgbuild.py check_output.json

# 3. Validate the result
python validate_pkgbuild.py

# 4. Test locally
makepkg -s
```

#### Full Workflow Testing

```bash
# Test the complete GitHub Actions workflow locally
python test_workflow.py --run
```

This simulates the entire automated process including:
- Version downgrade simulation
- Complete workflow execution in Docker
- Comprehensive validation
- Result reporting

### Branch Strategy

- **`main`**: Production branch - triggers actual AUR updates (no validation step)
- **`development`**: Testing branch - runs comprehensive validation + DEBUG mode (no AUR push)

**Important**: The 25+ validation checks only run automatically on the `development` branch. This ensures thorough testing before changes reach production.

### Validation System

The system performs 25+ comprehensive checks:

| Category | Checks |
|----------|--------|
| **Format** | Version format, pkgrel validation, commit hash format |
| **Content** | SHA512 checksums, electron version, source URLs |
| **Functionality** | Tool availability, URL accessibility, command syntax |
| **Integration** | Native titlebar fix, cursor.sh transformation |
| **Advanced** | Dynamic electron detection, actual file verification |

## 🔧 Advanced Features

### Electron Version Detection

The system automatically detects the correct Electron version by:
1. Extracting VSCode version from Cursor's `product.json`
2. Downloading VSCode source tarball
3. Parsing `package-lock.json` for Electron dependencies
4. Updating PKGBUILD with correct `electronXX` package

### Debug Mode

Enable verbose logging for troubleshooting:

```bash
DEBUG=true python check.py
DEBUG=true python update_pkgbuild.py check_output.json
```

## 🤝 Contributing

### Reporting Issues

- **Package Issues**: Report to [AUR cursor-bin page](https://aur.archlinux.org/packages/cursor-bin)
- **Automation Issues**: Create issues in this repository

### Development

1. Fork this repository
2. Create feature branch from `development`
3. Test changes with `python test_workflow.py --run`
4. Submit PR against `development` branch

### Adding New Checks

To add validation checks, modify `validate_pkgbuild.py`:

```python
# Add new check in validate_pkgbuild() function
results["checks"].append({
    "check": "your_check_name",
    "status": "pass" or "fail", 
    "message": "Description of what was checked"
})
```

## 📊 Monitoring

- **GitHub Actions**: Check workflow runs for automation status
- **AUR Package**: Monitor [cursor-bin](https://aur.archlinux.org/packages/cursor-bin) for updates
- **Issues**: Watch this repository for automation problems

## 🔗 Related Links

- [Cursor IDE Official Site](https://www.cursor.com)
- [AUR cursor-bin Package](https://aur.archlinux.org/packages/cursor-bin)
- [Arch Linux AUR Guidelines](https://wiki.archlinux.org/title/AUR_submission_guidelines)
- [Original PR #16 - .deb Migration](https://github.com/Gunther-Schulz/aur-cursor-bin-updater/pull/16)

---

**Note**: This repository maintains the AUR package automatically. End users should install `cursor-bin` directly from the AUR, not from this repository.
