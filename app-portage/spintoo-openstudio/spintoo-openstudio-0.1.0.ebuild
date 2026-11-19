# Copyright 2026 Gentoo Authors
# Distributed under the terms of the GNU General Public License v2

EAPI=8
DISTUTILS_USE_PEP517=setuptools
PYTHON_COMPAT=( python3_{13..14} )
inherit desktop distutils-r1

DESCRIPTION="Gentoo build-matrix planner for isolated libvirt environments"
HOMEPAGE="https://github.com/andiallen1979/Fragtoo"
S="${WORKDIR}/${P}"
LICENSE="MIT"
SLOT="0"
KEYWORDS="~amd64"

RDEPEND="
	dev-python/libvirt-python[${PYTHON_USEDEP}]
	dev-python/pyqt6[gui,widgets,${PYTHON_USEDEP}]
"

src_unpack() {
	mkdir -p "${S}" || die
	cp -a "${FILESDIR}/src/." "${S}/" || die
}

python_install_all() {
	distutils-r1_python_install_all
	domenu "${FILESDIR}/spintoo-openstudio.desktop"
}
