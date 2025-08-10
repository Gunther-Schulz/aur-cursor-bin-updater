# Maintainer: Gunther Schulz <dev@guntherschulz.de>

pkgname=cursor-bin
pkgver=1.4.2
pkgrel=1
pkgdesc='AI-first coding environment'
arch=('x86_64')
url="https://www.cursor.com"
license=('LicenseRef-Cursor_EULA')
depends=('ripgrep' 'xdg-utils'
  'gcc-libs' 'hicolor-icon-theme' 'libxkbfile' 'electron28')
options=(!strip) # Don't break ext of VSCode
_appimage="${pkgname}-${pkgver}.AppImage"
# _commit=test123456789
source=("${_appimage}::https://downloads.cursor.com/production/test123456789/linux/x64/Cursor-1.4.2-x86_64.AppImage"
https://gitlab.archlinux.org/archlinux/packaging/packages/code/-/raw/main/code.sh)
sha512sums=('4347b62fd647177c209fd9d232e5cc9ca864414a968f17eaef71772960d6b005f13f7910be4e30df605cb8345f9ef20566d29f309bb15d654e26ba76f8d62690'
            '937299c6cb6be2f8d25f7dbc95cf77423875c5f8353b8bd6cd7cc8e5603cbf8405b14dbf8bd615db2e3b36ed680fc8e1909410815f7f8587b7267a699e00ab37')

_app=usr/share/cursor/resources/app
package() {
  # Extract Electron version from depends array BEFORE changing directories
  _electron=$(grep -o "electron[0-9]*" "${startdir}/PKGBUILD" | head -1)

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

  mv usr "${pkgdir}"/usr

  # Create the modified cursor script
  sed -e "s|code-flags|cursor-flags|" \
      -e "s|/usr/lib/code|/${_app}|" \
      -e "s|/usr/lib/code/out/cli.js|/${_app}/out/cli.js|" \
      -e "s|/usr/lib/code/code.mjs|--app=/usr/share/cursor/resources/app|" \
      -e "s|name=electron|name=${_electron}|" \
      "${srcdir}"/code.sh > "${srcdir}"/cursor.sh

  # Check if sed succeeded and verify replacements
  if [ $? -eq 0 ]; then
      if grep -q "cursor-flags" "${srcdir}"/cursor.sh && \
         grep -q "name=${_electron}" "${srcdir}"/cursor.sh; then
          echo "sed replacements successful"

          # Additional verification: check that _electron is not empty
          if [ -z "${_electron}" ]; then
              echo "ERROR: _electron variable is empty - Electron version extraction failed"
              exit 1
          fi

          # Verify the final path will be correct
          if ! grep -q "exec /usr/lib/\${name}/electron" "${srcdir}"/cursor.sh; then
              echo "ERROR: exec path not found in generated script"
              exit 1
          fi

          # Verify all path replacements were successful
          if ! grep -q "/usr/share/cursor/resources/app/out/cli.js" "${srcdir}"/cursor.sh; then
              echo "ERROR: cli.js path replacement failed"
              exit 1
          fi

          if ! grep -q "app=/usr/share/cursor/resources/app" "${srcdir}"/cursor.sh; then
              echo "ERROR: app path replacement failed"
              exit 1
          fi

          # Verify no old paths remain
          if grep -q "/usr/lib/code" "${srcdir}"/cursor.sh; then
              echo "ERROR: old /usr/lib/code paths still present"
              exit 1
          fi

          echo "All verifications passed"
          install -Dm755 "${srcdir}"/cursor.sh "${pkgdir}"/usr/share/cursor/cursor
      else
          echo "ERROR: sed replacements failed - content not modified"
          exit 1
      fi
  else
      echo "ERROR: sed command failed"
      exit 1
  fi
}
