# Maintainer: Your Name <your.email@example.com>

pkgname=cursor-bin
pkgver=0.39.8
pkgrel=18
pkgdesc="Cursor App - AI-first coding environment"
arch=('x86_64')
url="https://www.cursor.com/"
license=('custom:Proprietary')  # Replace with the correct license if known
depends=('fuse2')
options=(!strip)
source_x86_64=("https://github.com/Gunther-Schulz/aur-cursor-bin-updater/releases/download/v${pkgver}/cursor-${pkgver}.AppImage" "cursor.png")
noextract=("cursor-${pkgver}.AppImage")
sha256sums_x86_64=('86e653cc8645018b4644c857182fb5b1dd25dace7dd7742458cf908c2b6c125d' 'SKIP')

package() {
    install -Dm755 "${srcdir}/cursor-${pkgver}.AppImage" "${pkgdir}/opt/${pkgname}/${pkgname}.AppImage"

    # Symlink executable to be called 'cursor'
    mkdir -p "${pkgdir}/usr/bin"
    ln -s "/opt/${pkgname}/${pkgname}.AppImage" "${pkgdir}/usr/bin/cursor"

    # Install the icon
    install -Dm644 "${srcdir}/cursor.png" "${pkgdir}/usr/share/icons/hicolor/512x512/apps/cursor.png"

    # Create a .desktop Entry
    mkdir -p "${pkgdir}/usr/share/applications"
    cat <<EOF > "${pkgdir}/usr/share/applications/cursor.desktop"
[Desktop Entry]
Name=Cursor
Exec=/usr/bin/cursor --no-sandbox %U
Terminal=false
Type=Application
Icon=cursor
StartupWMClass=cursor-url-handler
X-AppImage-Version=${pkgver}
MimeType=x-scheme-handler/cursor;
Categories=Utility;
EOF
}

post_install() {
    update-desktop-database -q
    xdg-icon-resource forceupdate
}