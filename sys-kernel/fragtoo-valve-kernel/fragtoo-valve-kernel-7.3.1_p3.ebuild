EAPI=8
PYTHON_COMPAT=( python3_{12..15} )
KERNEL_IUSE_GENERIC_UKI=1
inherit kernel-build
MY_P="linux-neptune-73-devel-${PV/_p/.valve}-1"
DESCRIPTION="Valve Neptune Steam Deck kernel built in Gentoo dist-kernel style"
HOMEPAGE="https://fragtoo.com"
SRC_URI="https://steamdeck-packages.steamos.cloud/archlinux-mirror/sources/jupiter-main/${MY_P}.src.tar.gz"
LICENSE="GPL-2"
KEYWORDS="~amd64"
BDEPEND="dev-vcs/git"

src_unpack() {
	default
	git clone "${WORKDIR}/linux-neptune-73-devel/archlinux-linux-neptune-devel" "${S}" || die
}

src_prepare() {
	default
	rm -f localversion* && echo "-p3-valve3" > localversion.10-fragtoo || die
	local ref="${WORKDIR}/linux-neptune-73-devel"
	local cfg="${WORKDIR}/fragtoo-valve.config"
	cp "${ref}/config.x86_64" "${cfg}" || die
	KCONFIG_CONFIG="${cfg}" "${S}/scripts/kconfig/merge_config.sh" -m -r "${cfg}" "${ref}/config-neptune" || die
	"${S}/scripts/config" --file "${cfg}" -d RUST -d DEBUG_INFO_BTF -d IKHEADERS -d LOCALVERSION_AUTO \
		--set-str DEFAULT_HOSTNAME "fragtoo" || die
	:
}

src_configure() {
	cp "${WORKDIR}/fragtoo-valve.config" .config || die
	kernel-build_merge_configs
	kernel-build_src_configure
}
