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
| `.github/workflows/update-aur.yml` | Automated GitHub Actions workflow |
| `PKGBUILD.sed` | The actual package build script |

See those files if you want to contribute.

### Automated Workflow

1. **🕐 Scheduled Check**: GitHub Actions runs daily (and on manual trigger)
2. **Generate PKGBUILD**: Generate PKGBUILD from templete.
3. **🔍 Check that PKGBUILD was changed**
4. **✅ Validation**: check quality
5. **🚀 AUR Publish**: Automatic commit and push to AUR *(main branch only)*

**Branch Behavior**:
- **Development**: Runs steps 1-4, skips AUR publish for safe testing
- **Main**: Runs steps 1-3 + 5, skips validation for faster production updates

## 🤝 Contributing

### Reporting Issues

- **Package Issues**: Report to [AUR cursor-bin page](https://aur.archlinux.org/packages/cursor-bin)
- **Automation Issues**: Create issues in this repository

### Development

1. Fork this repository
2. Submit PR

## 📊 Monitoring

- **GitHub Actions**: Check workflow runs for automation status
- **AUR Package**: Monitor [cursor-bin](https://aur.archlinux.org/packages/cursor-bin) for updates
- **Issues**: Watch this repository for automation problems

## 🔗 Related Links

- [Cursor IDE Official Site](https://www.cursor.com)
- [AUR cursor-bin Package](https://aur.archlinux.org/packages/cursor-bin)
- [Arch Linux AUR Guidelines](https://wiki.archlinux.org/title/AUR_submission_guidelines)

---

**Note**: This repository maintains the AUR package automatically. End users should install `cursor-bin` directly from the AUR, not from this repository.
