EAPI=8
inherit udev
DESCRIPTION="Steam Deck hardware udev rules, display rotation, and touchscreen calibration for Fragtoo"
HOMEPAGE="https://fragtoo.com"
LICENSE="GPL-2"
SLOT="0"
KEYWORDS="~amd64"
S="${WORKDIR}"

src_install() {
	udev_dorules "${FILESDIR}/99-fragtoo-steamdeck-touch.rules"
	insinto /etc/kernel/cmdline.d
	doins "${FILESDIR}/fragtoo-kcmdline.conf"
}

pkg_postinst() {
	udev_reload
	elog "Ensure your bootloader kernel cmdline includes: fbcon=rotate:1 video=eDP-1:panel_orientation=right_side_up"
}

pkg_postrm() {
	udev_reload
}
