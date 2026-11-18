EAPI=8
PYTHON_COMPAT=( python3_{12..15} )
KERNEL_IUSE_GENERIC_UKI=1
inherit kernel-build

DESCRIPTION="Vanilla Linux + Gentoo genpatches + Valve Steam Deck patchset (dist-kernel)"
HOMEPAGE="https://fragtoo.com"
SRC_URI="
	https://cdn.kernel.org/pub/linux/kernel/v7.x/linux-7.3.tar.xz
	https://cdn.kernel.org/pub/linux/kernel/v7.x/patch-${PV}.xz
	https://gentoo.org/pub/proj/dist-kernel/patchsets/7.3/linux-gentoo-patches-${PV}.tar.xz
	https://gentoo.org/proj/dist-kernel/gentoo-kernel-config.git/snapshot/gentoo-kernel-config-g19.tar.bz2
	https://gentoo.org/pub/proj/dist-kernel/config/fedora-kernel-config-${PV}-gentoo.tar.xz
	https://steamdeck-packages.steamos.cloud/archlinux-mirror/sources/jupiter-main/linux-neptune-73-devel-${PV}.valve3-1.src.tar.gz
"
S="${WORKDIR}/linux-7.3"
LICENSE="GPL-2"
KEYWORDS="~amd64"
IUSE="debug"
BDEPEND="dev-vcs/git sys-apps/diffutils"

PATCHES=(
	"${FILESDIR}/fix-hdmi-frl-status-polling-work-linkage.patch"
	"${FILESDIR}/fix-ath11k-unitest-makefile.patch"
	"${FILESDIR}/fix-binutils-247-module-relocs.patch"
)

src_unpack() {
	unpack linux-7.3.tar.xz patch-${PV}.xz linux-gentoo-patches-${PV}.tar.xz \
		gentoo-kernel-config-g19.tar.bz2 fedora-kernel-config-${PV}-gentoo.tar.xz
	mkdir -p "${WORKDIR}/vsrc" "${WORKDIR}/van" || die
	tar -xzf "${DISTDIR}/linux-neptune-73-devel-${PV}.valve3-1.src.tar.gz" -C "${WORKDIR}/vsrc" || die
	git clone -q "${WORKDIR}/vsrc/linux-neptune-73-devel/archlinux-linux-neptune-devel" "${WORKDIR}/valve" || die
	rm -rf "${WORKDIR}/valve/.git" || die
	tar -xJf "${DISTDIR}/linux-7.3.tar.xz" -C "${WORKDIR}/van" || die
	patch -d "${WORKDIR}/van/linux-7.3" -p1 -s < "${WORKDIR}/patch-${PV}" || die
	( cd "${WORKDIR}" && diff -Naur -x Makefile -x hid-asus.c -x amdgpu_dm_connector.c van/linux-7.3 valve ) > "${WORKDIR}/valve-deck.patch"
	rm -rf "${WORKDIR}/van" "${WORKDIR}/valve" "${WORKDIR}/vsrc" || die
}

src_prepare() {
	eapply "${WORKDIR}/patch-${PV}"
	eapply "${WORKDIR}/linux-gentoo-patches-${PV}"
	patch -p1 --forward --batch -r - < "${WORKDIR}/valve-deck.patch" || true
	default
}

src_configure() {
	cp "${WORKDIR}/fedora-kernel-config-${PV}-gentoo/kernel-x86_64-fedora.config" .config || die
	echo "CONFIG_LOCALVERSION=\"-fragtoo-dist\"" > "${T}/version.config" || die
	local d="${WORKDIR}/gentoo-kernel-config-g19"
	local f="${FILESDIR}"
	local cfgs=(
		"${T}/version.config" "${d}/base.config" "${d}/6.12+.config"
		"${f}/steamdeck-hw.config" "${f}/steamdeck-gpu.config"
		"${f}/steamdeck-audio.config" "${f}/steamdeck-sched.config"
	)
	use debug || cfgs+=( "${d}/no-debug.config" )
	kernel-build_merge_configs "${cfgs[@]}"
	kernel-build_src_configure
}
