EAPI=8
DESCRIPTION="Valve Jupiter Steam Deck EC fan controller daemon"
HOMEPAGE="https://fragtoo.com"
SRC_URI="https://steamdeck-packages.steamos.cloud/archlinux-mirror/sources/jupiter-main/jupiter-fan-control-${PV}-1.src.tar.gz"
LICENSE="MIT"
SLOT="0"
KEYWORDS="~amd64"
BDEPEND="dev-vcs/git"
RDEPEND="dev-lang/python dev-python/pyyaml"

src_unpack() {
	default
	git clone "${WORKDIR}/jupiter-fan-control/jupiter-fan-control" "${S}" || die
}

src_install() {
	rm -rf .git README.md pyproject.toml
	cp -a . "${D}/" || die
}
