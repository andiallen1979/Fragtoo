EAPI=8
DESCRIPTION="Valve SteamOS parity Portage make.conf and USE flag sets for Steam Deck (znver2)"
HOMEPAGE="https://fragtoo.com"
LICENSE="GPL-2"
SLOT="0"
KEYWORDS="~amd64"
RDEPEND="!sys-config/fragtoo-configs-custom"
S="${WORKDIR}"

src_install() {
	insinto /etc/portage/fragtoo
	doins "${FILESDIR}/make.conf.fragtoo"
	insinto /etc/portage/package.use
	doins "${FILESDIR}/fragtoo-valve.use"
}

pkg_postinst() {
	elog "Add 'source /etc/portage/fragtoo/make.conf.fragtoo' to your /etc/portage/make.conf"
}
