# Maintainer: Your Name <your.email@example.com>

pkgname=cursor-bin
pkgver=0.43.6
pkgrel=1
pkgdesc="Cursor App - AI-first coding environment"
arch=('x86_64')
url="https://www.cursor.com/"
license=('custom:Proprietary')  # Replace with the correct license if known
depends=('fuse2')
options=(!strip)
_appimage="${pkgname}-${pkgver}.AppImage"
source_x86_64=("${_appimage}::https://download.todesktop.com/230313mzl4w4u92/cursor-0.43.5-build-241127pdg4cnbu2-x86_64.AppImage" "cursor.png" "${pkgname}.desktop.in")
noextract=("${_appimage}")
sha512sums_x86_64=('dd30d038ff11703b3f5a860235a2a53cebdb07bc48f247cf9f31302acc05e5886b52fe518f5bad3e1492913684fa3df61dbbf2f8c52dd1abfa266801f2fff628'
                   'f948c5718c2df7fe2cae0cbcd95fd3010ecabe77c699209d4af5438215daecd74b08e03d18d07a26112bcc5a80958105fda724768394c838d08465fce5f473e7'
                   'e7e355524db7ddca2e02351f5af6ade791646b42434400f03f84e1068a43aadaa469ba6d5acbc16e6a3a7e52be4807b498585bea3f566e19b66414f6c3095154')

prepare() {
    # Set correct version in .desktop file
    sed "s/@@PKGVERSION@@/${pkgver}/g" "${srcdir}/${pkname}.desktop.in" > "${srcdir}/cursor-cursor.desktop"
}

package() {
    # Create directories
    install -d "${pkgdir}/opt/${pkgname}"
    install -d "${pkgdir}/usr/bin"
    install -d "${pkgdir}/usr/share/applications"
    install -d "${pkgdir}/usr/share/icons"

    # Install files with proper permissions
    install -m644 "${srcdir}/cursor-cursor.desktop" "${pkgdir}/usr/share/applications/cursor-cursor.desktop"
    install -m644 "${srcdir}/cursor.png" "${pkgdir}/usr/share/icons/cursor.png"
    install -m755 "${srcdir}/${_appimage}" "${pkgdir}/opt/${pkgname}/${pkgname}.AppImage"

    # Symlink executable to be called 'cursor'
    ln -s "/opt/${pkgname}/${pkgname}.AppImage" "${pkgdir}/usr/bin/cursor"
}

post_install() {
    update-desktop-database -q
    xdg-icon-resource forceupdate
}
