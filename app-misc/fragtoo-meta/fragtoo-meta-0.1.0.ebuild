EAPI=8
DESCRIPTION="Meta package for the fragtoo Gentoo overlay"
HOMEPAGE="https://codeberg.org{R}"
S="${WORKDIR}"
LICENSE="metapackage"
SLOT="0"
KEYWORDS="~amd64 ~arm64"
RDEPEND="
	app-misc/fragtoocfg
	app-portage/fragtoo-scripts
	sys-config/fragtoo-configs
	sys-kernel/fragtoo-kernel-config
"
