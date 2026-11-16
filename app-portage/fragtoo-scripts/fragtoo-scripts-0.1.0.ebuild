EAPI=8
DESCRIPTION="Repository maintenance and push scripts for fragtoo"
HOMEPAGE="https://codeberg.org{R}"
S="${WORKDIR}"
LICENSE="MIT"
SLOT="0"
KEYWORDS="~amd64 ~arm64"

src_install() {
	mkdir -p "${T}/bin" && tar -xJf "${FILESDIR}/fragtoo-scripts-bundle.tar.xz" -C "${T}/bin" || die
	dobin "${T}/bin"/*
}
