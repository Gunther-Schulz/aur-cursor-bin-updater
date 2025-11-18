# Testing Guide for Bash-Based Workflow

This guide explains how to safely test the bash-based PKGBUILD generation workflow without committing to AUR.

## 🛡️ Safe Testing Methods

### Method 1: Test on `development` Branch (Safest)

The workflow automatically stops before AUR publishing when run on the `development` branch.

**Steps:**
1. Create or switch to `development` branch:
   ```bash
   git checkout -b development
   git push -u origin development
   ```

2. Push your PR changes to the `development` branch

3. The workflow will:
   - ✅ Check for updates
   - ✅ Generate PKGBUILD
   - ✅ Validate PKGBUILD
   - ✅ Commit to GitHub repository
   - ❌ **STOP before AUR publishing** (line 128-130)

4. Review the generated PKGBUILD in the GitHub commit

**Advantages:**
- Full workflow test in GitHub Actions
- No risk of AUR commits
- Can review actual generated PKGBUILD
- Tests all GitHub Actions steps

### Method 2: Local Testing Script

Use the provided `test_bash_workflow.sh` script to test locally.

**Steps:**
```bash
# Run the test script
./test_bash_workflow.sh
```

**What it does:**
- Checks all dependencies
- Backs up current PKGBUILD
- Fetches latest version from Cursor API
- Downloads .deb file
- Calculates SHA512 checksum
- Determines Electron version
- Generates PKGBUILD from template
- Validates the generated PKGBUILD
- Optionally tests with `makepkg`

**Output:**
- `PKGBUILD.test` - Generated PKGBUILD
- `PKGBUILD.backup` - Backup of original PKGBUILD

**Advantages:**
- Fast iteration
- No network calls to GitHub/AUR
- Can test multiple times quickly
- Full control over the process

### Method 3: Test on a Fork

Create a fork and test there without affecting the main repository.

**Steps:**
1. Fork the repository on GitHub
2. Push your changes to a branch in your fork
3. The workflow will run but won't have AUR credentials
4. Review the workflow logs and generated PKGBUILD

**Advantages:**
- Complete isolation
- Can test full workflow
- No risk to main repository

### Method 4: Manual Workflow Dispatch

Trigger the workflow manually on a test branch.

**Steps:**
1. Push your changes to a test branch (e.g., `test-bash-workflow`)
2. Go to GitHub Actions tab
3. Click "Run workflow" → Select your test branch
4. Monitor the workflow execution

**Note:** Make sure the branch name is NOT `main` to avoid AUR publishing.

### Method 5: Force Update Test (Local)

Test the update detection by temporarily modifying PKGBUILD.

**Steps:**
```bash
# Temporarily change version in PKGBUILD to trigger update
sed -i 's/^pkgver=.*/pkgver=0.0.0/' PKGBUILD

# Run test script
./test_bash_workflow.sh

# Restore original
git checkout PKGBUILD
```

## 🔍 What to Check During Testing

### 1. Update Detection
- ✅ Correctly detects when update is needed
- ✅ Correctly detects when no update is needed
- ✅ Handles missing PKGBUILD (first run)

### 2. PKGBUILD Generation
- ✅ `pkgver` is set correctly
- ✅ `_commit` is set correctly
- ✅ `_electron` is determined correctly
- ✅ `sha512sum[0]` is calculated correctly
- ✅ `ripgrep` dependency is present
- ✅ All other dependencies are preserved

### 3. Validation
- ✅ All validation checks pass
- ✅ Errors are caught and reported

### 4. Workflow Steps
- ✅ Steps execute in correct order
- ✅ Conditional steps work correctly
- ✅ Step outputs are set correctly
- ✅ Branch detection works (development vs main)

## 🚨 Important Notes

1. **AUR Publishing Only on `main`**: The workflow only publishes to AUR when:
   - Branch is `main` (or `refs/heads/main`)
   - Update is needed
   - All previous steps succeed

2. **Development Branch Protection**: The workflow stops at line 128-130 when on `development` branch, preventing AUR commits.

3. **No Secrets on Forks**: If testing on a fork, AUR publishing will fail due to missing secrets (this is expected and safe).

4. **Local Testing**: The local test script doesn't require any secrets or GitHub access.

## 📝 Testing Checklist

Before merging to `main`:

- [ ] Test locally with `test_bash_workflow.sh`
- [ ] Test on `development` branch in GitHub Actions
- [ ] Verify PKGBUILD generation is correct
- [ ] Verify validation checks work
- [ ] Verify update detection works
- [ ] Verify no AUR commits on `development` branch
- [ ] Review generated PKGBUILD manually
- [ ] Test with an actual update scenario (if possible)

## 🐛 Troubleshooting

### Workflow fails with "update_needed not set"
- Check that the `check` step completed successfully
- Verify step outputs are being set correctly

### PKGBUILD validation fails
- Check that all sed replacements are working
- Verify template file has correct placeholders
- Check for special characters in values

### Electron version detection fails
- Check VSCode version extraction
- Verify GitHub API access
- Check jq parsing of package-lock.json

### Local test script fails
- Install missing dependencies: `sudo pacman -S libarchive jq curl`
- Check network connectivity
- Verify Cursor API is accessible

