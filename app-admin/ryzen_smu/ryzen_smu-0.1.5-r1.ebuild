# Copyright 2022-2026 Gentoo Authors
# Distributed under the terms of the GNU General Public License v2

EAPI=8

inherit linux-mod-r1

DESCRIPTION="Linux kernel driver that exposes access to the SMU for AMD Ryzen processors"
HOMEPAGE="https://gitlab.com/leogx9r/ryzen_smu"
SRC_URI="https://gitlab.com/leogx9r/ryzen_smu/-/archive/v${PV}/ryzen_smu-v${PV}.tar.bz2"
S="${WORKDIR}/ryzen_smu-v${PV}"

LICENSE="GPL-2+"
SLOT="0"
KEYWORDS="~amd64"

PATCHES=(
	"${FILESDIR}/ryzen_smu-kernel7.2.patch"
	"${FILESDIR}/ryzen_smu-zen5-linux7.patch"
)

src_compile() {
	local modlist=( ryzen_smu=extra )
	local modargs=(
		TARGET="${KV_FULL}"
		KERNEL_BUILD="${KV_OUT_DIR}"
	)
	linux-mod-r1_src_compile
}

src_install() {
	linux-mod-r1_src_install
	insinto /etc/modules-load.d
	doins "${FILESDIR}/ryzen_smu.conf"
	einstalldocs
}
