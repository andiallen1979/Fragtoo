EAPI=8
DESCRIPTION="Meta-package for Fragtoo Steam Deck gaming configuration and utilities"
HOMEPAGE="https://fragtoo.com"
LICENSE="metapackage"
SLOT="0"
KEYWORDS="~amd64"
IUSE="+bootcfg +conf +dsp +fan +hub +hw +kconf +scripts menu"
RDEPEND="
	bootcfg? ( sys-boot/gentool-bootcfg )
	conf? ( || ( sys-config/fragtoo-configs-valve sys-config/fragtoo-configs-custom ) )
	dsp? ( media-sound/steamdeck-dsp )
	fan? ( sys-power/jupiter-fan-control )
	hub? ( app-portage/fragtoo-hub )
	hw? ( sys-apps/fragtoo-hw-support )
	kconf? ( sys-kernel/fragtoo-kernel-config )
	menu? ( app-misc/gentool-menu )
	scripts? ( app-portage/gentool-scripts )
"
