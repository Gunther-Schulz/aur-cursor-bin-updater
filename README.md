# AUR Cursor Binary Package Updater

Automated maintenance for the [cursor-bin](https://aur.archlinux.org/packages/cursor-bin) AUR package. This repository monitors Cursor releases and keeps the PKGBUILD in sync for Arch Linux users.

## What This Repository Does

This is **not** an installation guide for Cursor. It is the automation that:

- Monitors Cursor releases via GitHub Actions (hourly, plus manual trigger)
- Generates PKGBUILDs with correct version, commit, checksum, and Electron dependency
- Publishes updates to the AUR automatically from `main`

The package itself repackages Cursor's official `.deb` and follows the same system-Electron approach as Arch's [`extra/code`](https://gitlab.archlinux.org/archlinux/packaging/packages/code) package.

## Installing Cursor (End Users)

Use your AUR helper:

```bash
yay -S cursor-bin
# or
paru -S cursor-bin
```

## Repository Layout

| File | Purpose |
|------|---------|
| `.github/workflows/update-aur.yml` | CI workflow: check, generate, commit, publish |
| `PKGBUILD.sed` | Template used to generate `PKGBUILD` |
| `PKGBUILD` | Current package definition (updated by CI) |
| `rg.sh` | Ripgrep wrapper shipped with the AUR package |
| `test_bash_workflow.sh` | Local test script mirroring the CI workflow |
| `TESTING.md` | Safe testing guide before merging to `main` |

## Automated Workflow

1. Query Cursor's stable update API and the AUR RPC for the current package state
2. Download the upstream `.deb`
3. Detect the required `electronXX` dependency from the bundled Cursor binary
4. Decide whether an update is needed (see below)
5. Generate `PKGBUILD` from `PKGBUILD.sed`
6. Commit to this repo and publish to AUR (`main` only)

### When an Update Triggers

An update runs if **any** of these are out of sync with upstream:

- Local `pkgver`, `_commit`, `_electron`, `pkgrel`, or checksum
- AUR version, pkgrel, or Electron dependency

Even when Cursor's version hasn't changed, a wrong Electron dependency (for example `electron` instead of `electron39`) will trigger a rebuild and **pkgrel bump**.

On a new upstream release, `pkgrel` resets to `1`.

### Electron Version Detection

Cursor ships a newer Electron than its embedded VSCode version reports, so the workflow reads the bundled binary inside the `.deb`:

```bash
ar x cursor.deb data.tar.xz
tar xJf data.tar.xz -O ./usr/share/cursor/cursor | strings | grep -oE 'Electron/[0-9]+'
```

The major version becomes the `_electron=electronXX` dependency and launcher path.

### Branch Behavior

| Branch | Commits to repo | Publishes to AUR |
|--------|-----------------|------------------|
| `main` | Yes | Yes |
| `development` | Yes | No (stops before SSH/AUR deploy) |

Use `development` to verify generated PKGBUILDs before they reach the AUR. See [TESTING.md](TESTING.md) for details.

## Local Development

### Test the workflow logic

```bash
./test_bash_workflow.sh
```

This mirrors the CI steps without committing or touching the AUR. Output is written to `PKGBUILD.test`.

Dependencies: `curl`, `jq`, `ar`, `tar`, `sha512sum`, `awk`, `grep`, `strings` (all standard on Arch).

### Test a build

```bash
./test_bash_workflow.sh
mv PKGBUILD.test PKGBUILD
makepkg -si
```

### Run GitHub Actions locally (optional)

```bash
yay -S act-bin
act workflow_dispatch
```

## Contributing

- **Package/runtime issues**: [AUR cursor-bin](https://aur.archlinux.org/packages/cursor-bin)
- **Automation issues**: issues/PRs in this repository

1. Branch from `development`
2. Test with `./test_bash_workflow.sh`
3. Optionally push to `development` and verify the GitHub Actions run
4. Open a PR against `development`, then merge to `main` when ready

## Monitoring

- [GitHub Actions](../../actions) — workflow runs
- [AUR cursor-bin](https://aur.archlinux.org/packages/cursor-bin) — published package

## Related Links

- [Cursor](https://www.cursor.com)
- [Arch `code` PKGBUILD](https://gitlab.archlinux.org/archlinux/packaging/packages/code) — upstream packaging this derives from
- [AUR submission guidelines](https://wiki.archlinux.org/title/AUR_submission_guidelines)
