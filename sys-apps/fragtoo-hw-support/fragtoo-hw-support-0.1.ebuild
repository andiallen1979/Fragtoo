EAPI=8
inherit udev
DESCRIPTION="Steam Deck udev rules, display rotation, and touchscreen calibration"
HOMEPAGE="https://fragtoo.com"
S="${WORKDIR}"
LICENSE="GPL-2"
SLOT="0"
KEYWORDS="~amd64"

src_install() {
	udev_dorules "${FILESDIR}/99-fragtoo-steamdeck-touch.rules"
	insinto /etc/kernel/cmdline.d
	doins "${FILESDIR}/fragtoo-kcmdline.conf"
}
pkg_postinst() { udev_reload; }
pkg_postrm() { udev_reload; }
