# Maintainer: Gunther Schulz <dev@guntherschulz.de>

pkgname=cursor-bin
pkgver=1.1.0
pkgrel=1
pkgdesc="AI-first coding environment"
arch=('x86_64')
url="https://www.cursor.com/"
license=(LicenseRef-Cursor_EULA)
depends=(alsa-lib cairo expat gtk3 libxkbfile nspr nss 
  ripgrep)
options=(!strip) # for sign of ext
_appimage="${pkgname}-${pkgver}.AppImage"
source_x86_64=("${_appimage}::https://downloads.cursor.com/production/b122cddec7bf4e6d7cc8badbae006d08b8e8105c/linux/x64/Cursor-1.1.0-x86_64.AppImage"
${pkgname}.sh)
# Don't include electron-flags.conf as https://gitlab.archlinux.org/archlinux/packaging/packages/code/-/raw/1.100.3-1/code.sh
sha512sums_x86_64=('44220bf0dd2889c6353b2a65c63703edb6980a93710a937fcd49136774193325b98af67b55a854a248e564c3cdd9974f55026a6b00e9e194bcebab112672377b'
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
