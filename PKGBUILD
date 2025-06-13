# Maintainer: Gunther Schulz <dev@guntherschulz.de>

pkgname=cursor-bin
pkgver=1.1.2
pkgrel=1
pkgdesc="AI-first coding environment"
arch=('x86_64')
url="https://www.cursor.com/"
license=(LicenseRef-Cursor_EULA)
depends=(alsa-lib cairo expat gtk3 libxkbfile nspr nss 
  ripgrep)
options=(!strip) # for sign of ext
_appimage="${pkgname}-${pkgver}.AppImage"
source_x86_64=("${_appimage}::https://downloads.cursor.com/production/b122cddec7bf4e6d7cc8badbae006d08b8e8105c/linux/x64/Cursor-1.1.2-x86_64.AppImage"
${pkgname}.sh)
# Don't include electron-flags.conf as https://gitlab.archlinux.org/archlinux/packaging/packages/code/-/raw/1.100.3-1/code.sh
sha512sums_x86_64=('c10b4b32b984ca260aed03f8a1f426c35d8763b0d3a878679c1c1ab9a0471e3447488bdaec5b072b2968f3149708c4f47d0947ee5ab7696ad9b1954aa99dada6'
                   'a1793990679da5c6b0af03103d3dc2614c0cc63b583e2be722fa5137b188f620f2c3c8248bae52921a2e85502112ab2e48c84ffc18c4e77274cd674be1515a05')

build() {
  rm -rf squashfs-root # for unclean BUILDDIR
  chmod +x ${_appimage}; ./${_appimage} --appimage-extract 1> /dev/null
  cd squashfs-root
  # Save 80MB+, translated by ext
  mv usr/share/cursor/locales/en-US.pak e.pak
  rm -r usr/share/cursor/{locales,resources/{linux,completions,appimageupdatetool.AppImage}}
  install -Dm644 e.pak usr/share/cursor/locales/en-US.pak
  # Avoid SUID at nonfree app: chmod 4755 chrome-sandbox
  # Replace binary with optimized one
  ln -svf /usr/bin/rg usr/share/cursor/resources/app/node_modules/@vscode/ripgrep/bin/rg
  # Patch launcher
  mv -v usr/share/cursor/{cursor,electron}
  install -Dvm755 "${srcdir}/${pkgname}.sh" usr/share/cursor/cursor
  # Fix unused icon from desktop entries
  rm -r usr/share/icons
  mv co.anysphere.cursor.png usr/share/pixmaps/co.anysphere.cursor.png
  # License
  install -d usr/share/licenses/${pkgname}
  mv -v usr/share/cursor/resources/app/LICENSE.txt usr/share/licenses/${pkgname}/LICENSE
  mv -v usr/share/cursor/resources/app/ThirdPartyNotices.txt usr/share/licenses/${pkgname}/
}

package(){
  cp -r --reflink=auto squashfs-root/usr "$pkgdir"/usr
}
