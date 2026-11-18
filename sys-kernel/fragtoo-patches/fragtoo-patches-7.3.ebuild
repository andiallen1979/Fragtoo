EAPI=8

DESCRIPTION="Fragtoo handheld gaming & Linux 7.3 compatibility patchset"
HOMEPAGE="https://fragtoo.com"
SRC_URI=""
S="${WORKDIR}"

LICENSE="GPL-2"
SLOT="7.3"
KEYWORDS="~amd64"

src_install() {
	insinto /usr/share/fragtoo-patches-${SLOT}
	doins "${FILESDIR}"/*.patch
}

pkg_postinst() {
	elog "Fragtoo kernel patches installed to ${EROOT}/usr/share/fragtoo-patches-${SLOT}/"
	elog "To apply automatically to custom kernels, symlink or copy them into:"
	elog "  /etc/portage/patches/sys-kernel/gentoo-sources/"
}
