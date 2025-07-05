# Maintainer: Gunther Schulz <dev@guntherschulz.de>
# Contributor: Konstantin <mazix@bk.ru>

pkgname=cursor-bin
pkgver=1.2.1
pkgrel=1
pkgdesc="Cursor – AI-first coding environment"
arch=('x86_64')
url='https://www.cursor.com/'
license=('custom:Proprietary')
depends=('fuse2' 'gtk3')
options=(!strip)

_appimage="${pkgname}-${pkgver}.AppImage"

# Note: AppImage is NOT listed here; we download it in prepare()
source_x86_64=(
  'cursor-bin.desktop.in'
  'cursor.png'
  'cursor-bin.sh'
)
sha512sums_x86_64=('SKIP' 'SKIP' 'SKIP')

prepare() {
  cd "${srcdir}"

  # Fetch AppImage if missing
  if [[ ! -f ${_appimage} ]]; then
    msg2 "Downloading ${_appimage} …"

    # custom URL override
    if [[ -n ${CURSOR_URL} ]]; then
      dl_url="${CURSOR_URL}"
      msg2 "Using CURSOR_URL=${dl_url}"
    else
      # scrape a fresh presigned link
      dl_url=$(curl -fsL https://www.cursor.so/download |
        grep -oP 'https://downloads.cursor.com/[^"]+x64/Cursor-[\d.]+-x86_64.AppImage' |
        head -n1)
    fi

    if [[ -z ${dl_url} ]]; then
      error "Could not obtain download URL. Supply CURSOR_URL or place the AppImage manually."
      exit 1
    fi

    for i in {1..3}; do
      curl -fL --retry 3 --retry-delay 2 -o "${_appimage}" "${dl_url}" && break
      sleep 5
    done

    [[ -s ${_appimage} ]] || { error "Download failed."; exit 1; }
  fi

  # Re-inject real checksum so future upgrades don’t re-download
  sha=$(sha512sum "${_appimage}" | awk '{print $1}')
  sed -i "s/^sha512sums_x86_64=.*/sha512sums_x86_64=('${sha}' 'SKIP' 'SKIP')/" \
      "${startdir}/PKGBUILD"

  # Prepare .desktop
  sed "s/@@PKGVERSION@@/${pkgver}/g" \
      cursor-bin.desktop.in > cursor.desktop
}

package() {
  install -Dm755 "${srcdir}/${_appimage}" \
    "${pkgdir}/opt/${pkgname}/${pkgname}.AppImage"

  install -Dm755 "${srcdir}/cursor-bin.sh" \
    "${pkgdir}/usr/bin/cursor"

  install -Dm644 "${srcdir}/cursor.desktop" \
    "${pkgdir}/usr/share/applications/cursor.desktop"
  install -Dm644 "${srcdir}/cursor.png" \
    "${pkgdir}/usr/share/icons/cursor.png"
}

post_install() {
  update-desktop-database -q
  xdg-icon-resource forceupdate
}
