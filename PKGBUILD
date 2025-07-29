# Maintainer: Gunther Schulz <dev@guntherschulz.de>

pkgname=cursor-bin
pkgver=1.3.4
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
_commit=bfb7c44bcb74430be0a6dd5edf885489879f2a2e
source=("${_appimage}::https://downloads.cursor.com/production/${_commit}/linux/x64/Cursor-${pkgver}-x86_64.AppImage"
https://gitlab.archlinux.org/archlinux/packaging/packages/code/-/raw/main/code.sh)
sha512sums=('28d754953f10176dbbd977d8fce57b4a0fd0022344a13a393563b488d1aaf2809a165e0ce835a8835319ad0fb31ffdea82fdbd25ad9ebaabbe12005aacd13391'
            '937299c6cb6be2f8d25f7dbc95cf77423875c5f8353b8bd6cd7cc8e5603cbf8405b14dbf8bd615db2e3b36ed680fc8e1909410815f7f8587b7267a699e00ab37')

_app=usr/share/cursor/resources/app
package() {
  rm -rf squashfs-root
  chmod +x ${_appimage}
  # Don't use upstream's broken resources
  for _f in co.anysphere.cursor.png usr/bin usr/share/{appdata,applications,bash-completion,mime,zsh}
    do ./${_appimage} --appimage-extract $_f > /dev/null
  done
  ./${_appimage} --appimage-extract usr/share/cursor/resources/app > /dev/null
  cd squashfs-root
  mv usr/share/zsh/{vendor-completions,site-functions}
  install -Dm644 co.anysphere.cursor.png -t usr/share/pixmaps
  ln -svf /usr/bin/rg ${_app}/node_modules/@vscode/ripgrep/bin/rg
  ln -svf /usr/bin/xdg-open ${_app}/node_modules/open/xdg-open

  # Allop packaging with other electron by editing PKGBUILD
  _electron=electron$(rg --no-messages -N -o -r '$1' '"electron": *"[^\d]*(\d+)' ${_app}/package.json)
  echo $_electron
  depends+=($_electron)
  mv usr "${pkgdir}"/usr
  sed -e "s|code-flags|cursor-flags|" -e "s|/usr/lib/code|/${_app}|" -e "s|/usr/lib/code/code.mjs|--app=/${_app}|" \
    -e "s|name=electron|name=${_electron}|" "${srcdir}"/code.sh | install -Dm755 /dev/stdin "${pkgdir}"/usr/share/cursor/cursor
}
