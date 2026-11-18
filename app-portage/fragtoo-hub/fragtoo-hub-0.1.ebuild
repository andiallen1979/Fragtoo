EAPI=8
DESCRIPTION="AUR-style community overlay registry and eselect connector for Gentoo"
HOMEPAGE="https://fragtoo.com"
LICENSE="GPL-2"
SLOT="0"
KEYWORDS="~amd64 ~arm64"
RDEPEND="dev-lang/python:3 app-eselect/eselect-repository"
S="${WORKDIR}"

src_install() {
	dobin "${FILESDIR}/fragtoo-hub"
}
