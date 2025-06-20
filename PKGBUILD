# Maintainer: Gunther Schulz <dev@guntherschulz.de>

pkgname=cursor-bin
pkgver=1.1.4
pkgrel=1
pkgdesc='AI-first coding environment'
arch=('x86_64')
url="https://www.cursor.com"
license=('LicenseRef-Cursor_EULA')
# electron* is added at package()
depends=('ripgrep' 'xdg-utils'
  'gcc-libs' 'hicolor-icon-theme' 'libxkbfile')
options=(!strip) # Don't break ext of VSCode
_appimage="${pkgname}-${pkgver}.AppImage"
_commit=e86fcc937643bc6385aebd982c1c66012c98caec
source=("${_appimage}::https://downloads.cursor.com/production/${_commit}/linux/x64/Cursor-${pkgver}-x86_64.AppImage"
https://gitlab.archlinux.org/archlinux/packaging/packages/code/-/raw/main/code.sh)
sha512sums=('86ca588558b08e30187d32963a07b68a79ad0e762845f20066b044cd82ebee4839466c92b7464cf59593054e2221eca4580566c08914a6ad102fd4e4e62a6ddc'
            '937299c6cb6be2f8d25f7dbc95cf77423875c5f8353b8bd6cd7cc8e5603cbf8405b14dbf8bd615db2e3b36ed680fc8e1909410815f7f8587b7267a699e00ab37')

_app=/usr/share/cursor/resources/app
prepare() {
  rm -rf squashfs-root # for unclean build
  chmod +x ${_appimage}
  ./${_appimage} --appimage-extract > /dev/null
  cd squashfs-root
  # Shell completions
  mv usr/share/zsh/{vendor-completions,site-functions}
  # Replace Electron
  mv .${_app} usr/lib/cursor
  rm -r usr/share/cursor
  install -d usr/share/cursor/resources
  mv usr/lib/cursor .${_app}
  # Replace rg and xdg-open
  ln -sf /usr/bin/rg       .${_app}/node_modules/@vscode/ripgrep/bin/rg
  ln -sf /usr/bin/xdg-open .${_app}/node_modules/open/xdg-open
  # License
  install -d usr/share/licenses/${pkgname}
  mv ./${_app}/LICENSE.txt usr/share/licenses/${pkgname}/LICENSE
  mv ./${_app}/ThirdPartyNotices.txt usr/share/licenses/${pkgname}/
  # Unused icon name by desktop entries... 1024^2 is slow...
  rm -r usr/share/icons
  install -Dm644 co.anysphere.cursor.png usr/share/pixmaps/co.anysphere.cursor.png
}

package(){
  # Allop packaging with other electron by editing PKGBUILD
  _electron=electron$(rg --no-messages -N -o -r '$1' '"electron": *"[^\d]*(\d+)' squashfs-root${_app}/package.json)
  echo $_electron
  depends+=($_electron)
  cp -r --reflink=auto squashfs-root/usr "${pkgdir}/usr"
  sed -e "s|code-flags|cursor-flags|" -e "s|/usr/lib/code|${_app}|" -e "s|/usr/lib/code/code.mjs|--app=${_app}|" \
    -e "s|name=electron|name=${_electron}|" code.sh | install -Dm755 /dev/stdin "${pkgdir}"/usr/share/cursor/cursor
}
