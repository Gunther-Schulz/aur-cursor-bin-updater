# Maintainer: Gunther Schulz <dev@guntherschulz.de>

pkgname=cursor-bin
pkgver=1.6.23
pkgrel=1
pkgdesc='AI-first coding environment'
arch=('x86_64')
url="https://www.cursor.com"
license=('LicenseRef-Cursor_EULA')
# electron* is added at package()
depends=('ripgrep' 'xdg-utils'
  'gcc-libs' 'hicolor-icon-theme' 'libxkbfile')
options=(!strip)                                 # Don't break ext of VSCode
_commit=9b5f3f4f2368631e3455d37672ca61b6dce8543e # sed'ded at GitHub WF
source=("https://downloads.cursor.com/production/9b5f3f4f2368631e3455d37672ca61b6dce8543e/linux/x64/deb/amd64/deb/cursor_1.6.23_amd64.deb"
  https://gitlab.archlinux.org/archlinux/packaging/packages/code/-/raw/main/code.sh)
sha512sums=('c64bff876cde6b92881305854dc529e8f11efaedb46a1b2fda47cb9d5fe7b56807a22b57587381644e8874c20cae142a5a94909c3c431aae0929a08c0ed5cff7'
  '937299c6cb6be2f8d25f7dbc95cf77423875c5f8353b8bd6cd7cc8e5603cbf8405b14dbf8bd615db2e3b36ed680fc8e1909410815f7f8587b7267a699e00ab37')

_app=usr/share/cursor/resources/app
package() {
  # Exclude electron
  bsdtar -xf data.tar.xz --exclude 'usr/share/cursor/[^r]*' --exclude 'usr/share/windsurf/*.pak'
  mv usr/share/zsh/{vendor-completions,site-functions}
  ln -svf /usr/bin/rg ${_app}/node_modules/@vscode/ripgrep/bin/rg
  ln -svf /usr/bin/xdg-open ${_app}/node_modules/open/xdg-open

  # Determine Electron major from the bundled app (fallback to 34 if detection fails)
  _electron_major="$(grep -oE '\"electron\"[[:space:]]*:[[:space:]]*\"[0-9]+' "${_app}/product.json" 2>/dev/null | grep -oE '[0-9]+' | head -1)"
  _electron="electron${_electron_major:-34}"
  echo "$_electron"
  depends+=("$_electron")

  # Install payload
  mv usr "${pkgdir}"/usr

  # Build the launcher from code.sh:
  # - rename flags to cursor-flags
  # - point runtime to the packaged app directory (NO --app= …)
  # - set the Electron binary name we depend on
  sed -e "s|code-flags|cursor-flags|" \
    -e "s|/usr/lib/code|/${_app}|" \
    -e "s|/usr/lib/code/code.mjs|/${_app}|" \
    -e "s|name=electron|name=${_electron}|" \
    "${srcdir}"/code.sh | install -Dm755 /dev/stdin "${pkgdir}"/usr/share/cursor/cursor

  install -d "${pkgdir}"/usr/bin
  ln -sf /usr/share/cursor/cursor "${pkgdir}"/usr/bin/cursor

  # Do NOT patch runtime JS. Users who want native decorations can set:
  #   "window.titleBarStyle": "native"
}
