EAPI=8
DESCRIPTION="Valve SteamOS parity Portage make.conf and USE sets for Steam Deck"
HOMEPAGE="https://fragtoo.com"
S="${WORKDIR}"
LICENSE="GPL-2"
SLOT="0"
KEYWORDS="~amd64"

src_install() {
	insinto /etc/portage/fragtoo
	doins "${FILESDIR}/make.conf.fragtoo"
	insinto /etc/portage/package.use
	doins "${FILESDIR}/fragtoo-valve.use"
	insinto /etc/portage/package.license
	doins "${FILESDIR}/fragtoo-valve.license"
}
