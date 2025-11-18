#!/bin/bash
# Local test script for the bash-based PKGBUILD generation workflow
# This simulates what the GitHub Actions workflow does without committing anything

set -e

echo "🧪 Testing bash-based PKGBUILD generation workflow"
echo "=================================================="
echo ""

# Check dependencies
echo "📦 Checking dependencies..."
for cmd in curl jq bsdtar sha512sum sed grep; do
    if ! command -v $cmd &> /dev/null; then
        echo "❌ Missing: $cmd"
        exit 1
    fi
done
echo "✓ All dependencies available"
echo ""

# Check if PKGBUILD.sed exists
if [ ! -f PKGBUILD.sed ]; then
    echo "❌ PKGBUILD.sed not found!"
    exit 1
fi

# Backup current PKGBUILD if it exists
if [ -f PKGBUILD ]; then
    echo "💾 Backing up current PKGBUILD to PKGBUILD.backup"
    cp PKGBUILD PKGBUILD.backup
    CURRENT_PKGVER=$(grep -E '^pkgver=' PKGBUILD | cut -d'=' -f2)
    CURRENT_COMMIT=$(grep -E '^_commit=' PKGBUILD | cut -d'=' -f2 | sed 's/ #.*//')
else
    CURRENT_PKGVER=""
    CURRENT_COMMIT=""
fi

echo ""
echo "🔍 Checking for updates..."
URL='https://cursor.com/api/download?platform=linux-x64&releaseTrack=stable'

# Get latest version info
NEW_PKGVER=$(curl -s "$URL" | jq -r .version)
NEW_COMMIT=$(curl -s "$URL" | jq -r .commitSha)

echo "Current version: ${CURRENT_PKGVER:-none}"
echo "Current commit: ${CURRENT_COMMIT:-none}"
echo "New version: ${NEW_PKGVER}"
echo "New commit: ${NEW_COMMIT}"
echo ""

# Check if update is needed
if [ "$CURRENT_PKGVER" = "$NEW_PKGVER" ] && [ "$CURRENT_COMMIT" = "$NEW_COMMIT" ]; then
    echo "ℹ️  No update needed. Current version matches latest."
    echo ""
    echo "💡 To force a test, you can temporarily modify PKGBUILD version"
    exit 0
fi

echo "📥 Update needed! Generating PKGBUILD..."
echo ""

# Download .deb file
echo "⬇️  Downloading .deb file..."
curl -s "https://downloads.cursor.com/production/${NEW_COMMIT}/linux/x64/deb/amd64/deb/cursor_${NEW_PKGVER}_amd64.deb" -o /tmp/cursor_test.deb

# Calculate SHA512
echo "🔐 Calculating SHA512 checksum..."
NEW_SHA=$(sha512sum /tmp/cursor_test.deb | cut -d ' ' -f 1)
echo "SHA512: ${NEW_SHA:0:20}..."

# Extract VSCode version from product.json
echo "📦 Extracting VSCode version..."
CODE_VERSION=$(bsdtar xOf /tmp/cursor_test.deb data.tar.xz 2>/dev/null | bsdtar xOf - ./usr/share/cursor/resources/app/product.json 2>/dev/null | jq -r .vscodeVersion)
echo "VSCode version: ${CODE_VERSION}"

# Get Electron version from VSCode's package-lock.json
echo "⚡ Determining Electron version..."
_ELECTRON=electron$(curl -sL "https://github.com/microsoft/vscode/raw/refs/tags/${CODE_VERSION}/package-lock.json" | jq -r '.packages."".devDependencies.electron |split(".")|.[0]')
echo "Electron: ${_ELECTRON}"
echo ""

# Generate PKGBUILD from template
echo "📝 Generating PKGBUILD from template..."
# Use awk for sha512sum replacement as sed has issues with brackets
awk -v pkgver="$NEW_PKGVER" \
    -v commit="$NEW_COMMIT" \
    -v sha="$NEW_SHA" \
    -v electron="$_ELECTRON" \
    'BEGIN {OFS=""} 
     /^pkgver=/ {print "pkgver=" pkgver; next}
     /^_commit=/ {print "_commit=" commit " # sed'\''ded at GitHub WF"; next}
     /^sha512sums\[0\]=/ {print "sha512sums[0]=" sha; next}
     /^_electron=/ {print "_electron=" electron; next}
     {print}' PKGBUILD.sed > PKGBUILD.test || {
    echo "❌ ERROR: Failed to generate PKGBUILD"
    exit 1
}

echo ""
echo "✅ Validation checks..."
# Temporarily disable exit on error for validation
set +e
VALIDATION_FAILED=0

# Basic validation
if ! grep -q "^pkgver=${NEW_PKGVER}$" PKGBUILD.test; then
    echo "❌ ERROR: pkgver not set correctly"
    VALIDATION_FAILED=1
else
    echo "✓ pkgver is correct"
fi

if ! grep -q "^_commit=${NEW_COMMIT}" PKGBUILD.test; then
    echo "❌ ERROR: _commit not set correctly"
    VALIDATION_FAILED=1
else
    echo "✓ _commit is correct"
fi

if ! grep -q "^_electron=${_ELECTRON}$" PKGBUILD.test; then
    echo "❌ ERROR: _electron not set correctly"
    VALIDATION_FAILED=1
else
    echo "✓ _electron is correct"
fi

if ! grep -q "^sha512sums\[0\]=${NEW_SHA}" PKGBUILD.test; then
    echo "❌ ERROR: sha512sum not set correctly"
    echo "   Expected: sha512sum[0]=${NEW_SHA:0:20}..."
    echo "   Got: $(grep '^sha512sums\[0\]=' PKGBUILD.test || echo 'not found')"
    VALIDATION_FAILED=1
else
    echo "✓ sha512sum is correct"
fi

# Check for ripgrep dependency
if ! grep -q "ripgrep" PKGBUILD.test; then
    echo "❌ ERROR: ripgrep dependency missing!"
    VALIDATION_FAILED=1
else
    echo "✓ ripgrep dependency present"
fi

echo ""

set -e
if [ $VALIDATION_FAILED -eq 1 ]; then
    echo "❌ Validation failed!"
    echo ""
    echo "Generated PKGBUILD content (for debugging):"
    echo "============================================"
    if [ -f PKGBUILD.test ]; then
        cat PKGBUILD.test
    else
        echo "PKGBUILD.test was not created!"
    fi
    exit 1
fi

echo "✅ All validations passed!"
echo ""
echo "📄 Generated PKGBUILD:"
echo "========================"
cat PKGBUILD.test
echo ""

# Optionally test with makepkg (if on Arch Linux)
if command -v makepkg &> /dev/null; then
    read -p "🧪 Test with makepkg? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo ""
        echo "🧪 Testing PKGBUILD with makepkg (dry run)..."
        cp PKGBUILD.test PKGBUILD
        makepkg --verifysource --noconfirm || echo "⚠️  makepkg test had issues (this is expected if source files aren't available)"
        if [ -f PKGBUILD.backup ]; then
            mv PKGBUILD.backup PKGBUILD
        fi
    fi
fi

echo ""
echo "📋 Summary:"
echo "==========="
echo "Generated PKGBUILD saved as: PKGBUILD.test"
echo "Original PKGBUILD preserved as: PKGBUILD.backup (if it existed)"
echo ""
echo "To review the generated PKGBUILD:"
echo "  cat PKGBUILD.test"
echo ""
echo "To compare with current PKGBUILD:"
echo "  diff PKGBUILD PKGBUILD.test"
echo ""
echo "To restore original PKGBUILD:"
echo "  mv PKGBUILD.backup PKGBUILD"
echo ""
echo "To use the generated PKGBUILD:"
echo "  mv PKGBUILD.test PKGBUILD"
echo ""

