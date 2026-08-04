# Maintainer: Gunther Schulz <dev@guntherschulz.de>

pkgname=cursor-bin
pkgver=3.14.27
pkgrel=1
pkgdesc='AI-first coding environment'
arch=('x86_64')
url="https://www.cursor.com"
license=('LicenseRef-Cursor_EULA')
# upstream uses Electron newer than internal VSCode
_electron=electron40
depends=(xdg-utils ripgrep $_electron nodejs
  'gcc-libs' 'hicolor-icon-theme' 'libxkbfile')
options=(!strip !debug) # Don't break ext of VSCode
_commit=047548b00c1a079373d74d00183f32510a4a41e1
source=("https://downloads.cursor.com/production/${_commit}/linux/x64/deb/amd64/deb/cursor_${pkgver}_amd64.deb"
"https://gitlab.archlinux.org/archlinux/packaging/packages/code/-/raw/main/code."{sh,mjs}
rg.sh)
sha512sums=('SKIP'
  '937299c6cb6be2f8d25f7dbc95cf77423875c5f8353b8bd6cd7cc8e5603cbf8405b14dbf8bd615db2e3b36ed680fc8e1909410815f7f8587b7267a699e00ab37'
  '793f9ff6306e3992ac89802d98110cba288ea1181a901467333293b7d76182ef9792c2a39ff49d9347a18a174b1f42bc58862091dff583f4146c2704eea28033'
  'e79fe7659f59d1ae02fc68816399bfd31587315df6cdb6ccf1d0ca76f7cdc692c2a42b30591c0091147bd97ef14b1c7745dc26bd7cb3ea6bba45698e5044fa2a')
sha512sums[0]=918341578824c8e0772ed54492263e1a07fdf7ed5f1a86f9b90a2f8aaf5433719b7f89e8e12b590c51f0062bbf7e21c221cc7cf0cdbe5a5c2099d656e0b3ff06
noextract=(cursor_${pkgver}_amd64.deb) # avoid double tarball
_app=usr/share/cursor/resources/app
package() {
  # Exclude electron
  bsdtar -xOf ${noextract[0]} data.tar.xz | tar -xJf - -C "$pkgdir" \
    --exclude 'usr/share/cursor/[^r]*' --exclude 'usr/share/cursor/*.pak'
  cd "$pkgdir"
  mv usr/share/zsh/{vendor-completions,site-functions}
  ln -sf /usr/bin/node ${_app}/resources/helpers/node
  install -Dm755 "${srcdir}/rg.sh" ${_app}/node_modules/@vscode/ripgrep/bin/rg
  ln -sf /usr/bin/xdg-open ${_app}/node_modules/open/xdg-open
  sed -e "1s|.*|#!/usr/lib/${_electron}/electron|" \
      -e "s|code-oss|cursor|g" -e "s|code.mjs|cursor.mjs|g" \
    "${srcdir}"/code.mjs | install -Dm644 /dev/stdin "${pkgdir}/${_app}/cursor.mjs"
  sed -e "s|code-flags|cursor-flags|" -e "s|/usr/lib/code|/${_app}|" -e "s|/usr/lib/code/code.mjs|/${_app}/cursor.mjs|" \
    -e "s|name=electron|name=${_electron}|" "${srcdir}"/code.sh | install -Dm755 /dev/stdin "${pkgdir}"/usr/share/cursor/cursor
  install -d "$pkgdir"/usr/bin
  ln -sf /usr/share/cursor/cursor "$pkgdir"/usr/bin/cursor
}
