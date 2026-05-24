#!/bin/bash
# Local test script for the bash-based PKGBUILD generation workflow
# Mirrors .github/workflows/update-aur.yml without committing anything

set -e

echo "🧪 Testing bash-based PKGBUILD generation workflow"
echo "=================================================="
echo ""

detect_electron_from_deb() {
  local deb=$1 tmpdir major
  tmpdir=$(mktemp -d)
  cp "$deb" "$tmpdir/pkg.deb"
  (cd "$tmpdir" && ar x pkg.deb data.tar.xz)
  major=$(tar xJf "$tmpdir/data.tar.xz" -O ./usr/share/cursor/cursor \
    | strings | grep -oE 'Electron/[0-9]+' | head -1 | cut -d/ -f2)
  rm -rf "$tmpdir"
  if [ -z "$major" ]; then
    echo "ERROR: Failed to detect Electron version from .deb" >&2
    exit 1
  fi
  echo "electron${major}"
}

echo "📦 Checking dependencies..."
for cmd in curl jq ar tar sha512sum awk grep strings; do
  if ! command -v $cmd &> /dev/null; then
    echo "❌ Missing: $cmd"
    exit 1
  fi
done
echo "✓ All dependencies available"
echo ""

if [ ! -f PKGBUILD.sed ]; then
  echo "❌ PKGBUILD.sed not found!"
  exit 1
fi

if [ -f PKGBUILD ]; then
  CURRENT_PKGVER=$(grep -E '^pkgver=' PKGBUILD | cut -d'=' -f2)
  CURRENT_PKGREL=$(grep -E '^pkgrel=' PKGBUILD | cut -d'=' -f2)
  CURRENT_PKGREL=${CURRENT_PKGREL:-1}
  CURRENT_COMMIT=$(grep -E '^_commit=' PKGBUILD | cut -d'=' -f2 | sed 's/ #.*//')
  CURRENT_ELECTRON=$(grep -E '^_electron=' PKGBUILD | cut -d'=' -f2)
  CURRENT_SHA=$(grep -E '^sha512sums\[0\]=' PKGBUILD | cut -d'=' -f2)
else
  CURRENT_PKGVER=""
  CURRENT_PKGREL=1
  CURRENT_COMMIT=""
  CURRENT_ELECTRON=""
  CURRENT_SHA=""
fi

echo "🔍 Checking for updates..."
echo "Local version: ${CURRENT_PKGVER:-none}-${CURRENT_PKGREL:-?} (commit: ${CURRENT_COMMIT:0:8}, ${CURRENT_ELECTRON:-unknown})"

AUR_PKGVER=""
AUR_PKGREL=""
AUR_ELECTRON=""
aur_response=$(curl -sf "https://aur.archlinux.org/rpc/?v=5&type=info&arg[]=cursor-bin" || true)
if [ -n "$aur_response" ]; then
  aur_version=$(echo "$aur_response" | jq -r '.results[0].Version // empty')
  AUR_PKGVER=$(echo "$aur_version" | cut -d'-' -f1)
  AUR_PKGREL=$(echo "$aur_version" | cut -d'-' -f2)
  AUR_ELECTRON=$(echo "$aur_response" | jq -r '.results[0].Depends[]? | select(test("^electron"))' | head -1)
fi
echo "AUR version: ${AUR_PKGVER:-unknown}-${AUR_PKGREL:-?} (${AUR_ELECTRON:-unknown electron dep})"

api_response=$(curl -sf "https://api2.cursor.sh/updates/api/update/linux-x64/cursor/0.0.0/deadbeef/stable")
if [ -z "$api_response" ]; then
  echo "❌ ERROR: Failed to get response from update API"
  exit 1
fi

NEW_PKGVER=$(echo "$api_response" | jq -r '.version')
api_url=$(echo "$api_response" | jq -r '.url')
NEW_COMMIT=$(echo "$api_url" | sed -n 's|.*/production/\([^/]*\).*|\1|p')

if [ -z "$NEW_PKGVER" ] || [ -z "$NEW_COMMIT" ]; then
  echo "❌ ERROR: Failed to extract version or commit from API response"
  exit 1
fi

echo "Latest: $NEW_PKGVER (commit: ${NEW_COMMIT:0:8})"
echo ""

echo "⬇️  Downloading .deb file..."
curl -sf "https://downloads.cursor.com/production/${NEW_COMMIT}/linux/x64/deb/amd64/deb/cursor_${NEW_PKGVER}_amd64.deb" -o /tmp/cursor_test.deb

echo "🔐 Calculating SHA512 checksum..."
NEW_SHA=$(sha512sum /tmp/cursor_test.deb | cut -d ' ' -f 1)
echo "SHA512: ${NEW_SHA:0:20}..."

echo "⚡ Detecting Electron version from bundled binary..."
_ELECTRON=$(detect_electron_from_deb /tmp/cursor_test.deb)
echo "Detected Electron dependency: ${_ELECTRON}"
echo ""

if [ "$CURRENT_PKGVER" != "$NEW_PKGVER" ] || [ "$CURRENT_COMMIT" != "$NEW_COMMIT" ]; then
  NEW_PKGREL=1
elif [ "$CURRENT_ELECTRON" != "$_ELECTRON" ]; then
  NEW_PKGREL=$((CURRENT_PKGREL + 1))
else
  NEW_PKGREL=$CURRENT_PKGREL
fi

LOCAL_NEEDS_UPDATE=false
[ "$CURRENT_PKGVER" != "$NEW_PKGVER" ] && LOCAL_NEEDS_UPDATE=true
[ "$CURRENT_COMMIT" != "$NEW_COMMIT" ] && LOCAL_NEEDS_UPDATE=true
[ "$CURRENT_ELECTRON" != "$_ELECTRON" ] && LOCAL_NEEDS_UPDATE=true
[ "$CURRENT_PKGREL" != "$NEW_PKGREL" ] && LOCAL_NEEDS_UPDATE=true
[ "$CURRENT_SHA" != "$NEW_SHA" ] && LOCAL_NEEDS_UPDATE=true

AUR_NEEDS_UPDATE=false
[ "${AUR_PKGVER:-}" != "$NEW_PKGVER" ] && AUR_NEEDS_UPDATE=true
[ "${AUR_PKGREL:-}" != "$NEW_PKGREL" ] && AUR_NEEDS_UPDATE=true
[ "${AUR_ELECTRON:-}" != "$_ELECTRON" ] && AUR_NEEDS_UPDATE=true

if [ "$LOCAL_NEEDS_UPDATE" = false ] && [ "$AUR_NEEDS_UPDATE" = false ]; then
  echo "ℹ️  No update needed. Local and AUR match latest upstream."
  exit 0
fi

if [ "$CURRENT_ELECTRON" != "$_ELECTRON" ]; then
  echo "📥 Update needed: electron dependency fix (${CURRENT_ELECTRON:-none} -> ${_ELECTRON}, pkgrel ${NEW_PKGREL})"
else
  echo "📥 Update needed!"
fi
echo ""

echo "📝 Generating PKGBUILD from template..."
awk -v pkgver="$NEW_PKGVER" \
    -v pkgrel="$NEW_PKGREL" \
    -v commit="$NEW_COMMIT" \
    -v sha="$NEW_SHA" \
    -v electron="$_ELECTRON" \
    'BEGIN {OFS=""} 
     /^pkgver=/ {print "pkgver=" pkgver; next}
     /^pkgrel=/ {print "pkgrel=" pkgrel; next}
     /^_commit=/ {print "_commit=" commit; next}
     /^sha512sums\[0\]=/ {print "sha512sums[0]=" sha; next}
     /^_electron=/ {print "_electron=" electron; next}
     {print}' PKGBUILD.sed > PKGBUILD.test || {
  echo "❌ ERROR: Failed to generate PKGBUILD"
  exit 1
}

echo ""
echo "✅ Validation checks..."
set +e
VALIDATION_FAILED=0

if ! grep -q "^pkgver=${NEW_PKGVER}$" PKGBUILD.test; then
  echo "❌ ERROR: pkgver not set correctly"
  VALIDATION_FAILED=1
else
  echo "✓ pkgver is correct"
fi

if ! grep -q "^pkgrel=${NEW_PKGREL}$" PKGBUILD.test; then
  echo "❌ ERROR: pkgrel not set correctly"
  VALIDATION_FAILED=1
else
  echo "✓ pkgrel is correct"
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
  echo "   Expected: sha512sums[0]=${NEW_SHA:0:20}..."
  echo "   Got: $(grep '^sha512sums\[0\]=' PKGBUILD.test || echo 'not found')"
  VALIDATION_FAILED=1
else
  echo "✓ sha512sum is correct"
fi

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
  cat PKGBUILD.test
  exit 1
fi

echo "✅ All validations passed!"
echo ""
echo "📄 Generated PKGBUILD:"
echo "========================"
cat PKGBUILD.test
echo ""

if command -v makepkg &> /dev/null; then
  read -p "🧪 Test with makepkg? (y/N) " -n 1 -r
  echo
  if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "🧪 Testing PKGBUILD with makepkg (dry run)..."
    if [ -f PKGBUILD ]; then
      cp PKGBUILD PKGBUILD.backup
    fi
    cp PKGBUILD.test PKGBUILD
    makepkg --verifysource --noconfirm || echo "⚠️  makepkg test had issues (this is expected if source files aren't available)"
    if [ -f PKGBUILD.backup ]; then
      mv PKGBUILD.backup PKGBUILD
      echo "✓ Restored original PKGBUILD"
    fi
  fi
fi

echo ""
echo "📋 Summary:"
echo "==========="
echo "Generated PKGBUILD saved as: PKGBUILD.test"
echo "Target version: ${NEW_PKGVER}-${NEW_PKGREL}"
echo "Electron dependency: ${_ELECTRON}"
echo ""
echo "To review the generated PKGBUILD:"
echo "  cat PKGBUILD.test"
echo ""
echo "To compare with current PKGBUILD:"
echo "  diff PKGBUILD PKGBUILD.test"
echo ""
echo "To use the generated PKGBUILD:"
echo "  mv PKGBUILD.test PKGBUILD"
echo ""
