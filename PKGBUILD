# Maintainer: Gunther Schulz <dev@guntherschulz.de>

pkgname=cursor-bin
pkgver=0.48.8
pkgrel=1
pkgdesc="Cursor App - AI-first coding environment"
arch=('x86_64')
url="https://www.cursor.com/"
license=('custom:Proprietary')  # Replace with the correct license if known
depends=('fuse2' 'gtk3')
options=(!strip)
_appimage="${pkgname}-${pkgver}.AppImage"
source_x86_64=("${_appimage}::https://downloads.cursor.com/production/7801a556824585b7f2721900066bc87c4a09b743/linux/x64/Cursor-0.48.8-x86_64.AppImage" "cursor.png" "${pkgname}.desktop.in" "${pkgname}.sh")
noextract=("${_appimage}")
sha512sums_x86_64=('460631fd743cc0b479209daa6c525688996b08c335eb182440ed68674b6258c350ca6fc7e07d345a1c9a9f7781d1383aeb66ba01ba7fa4b75a432d4a754ff21f'
                   'f948c5718c2df7fe2cae0cbcd95fd3010ecabe77c699209d4af5438215daecd74b08e03d18d07a26112bcc5a80958105fda724768394c838d08465fce5f473e7'
                   '813d42d46f2e6aad72a599c93aeb0b11a668ad37b3ba94ab88deec927b79c34edf8d927e7bb2140f9147b086562736c3f708242183130824dd74b7a84ece67aa'
                   'ec3fa93a7df3ac97720d57e684f8745e3e34f39d9976163ea0001147961ca4caeb369de9d1e80c877bb417a0f1afa49547d154dde153be7fe6615092894cff47')

prepare() {
    # Set correct version in .desktop file
    sed "s/@@PKGVERSION@@/${pkgver}/g" "${srcdir}/${pkgname}.desktop.in" > "${srcdir}/cursor-cursor.desktop"
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

    # Install executable to be called 'cursor', that can load user flags from $XDG_CONFIG_HOME/cursor-flags.conf
    install -m755 "${srcdir}/${pkgname}.sh" "${pkgdir}/usr/bin/cursor"
}

post_install() {
    update-desktop-database -q
    xdg-icon-resource forceupdate
}
