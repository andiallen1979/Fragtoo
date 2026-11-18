EAPI=8
DESCRIPTION="Meta-package for Fragtoo Steam Deck & handheld gaming configuration and utilities"
HOMEPAGE="https://fragtoo.com"
LICENSE="metapackage"
SLOT="0"
KEYWORDS="~amd64"
IUSE="+bootcfg +conf +dsp +fan +fkernel gkernel +hub +hw +kconf menu patches +ryzen +scripts vkernel +profiles"
RDEPEND="
	profiles? ( app-portage/gentool-profiles )
	bootcfg? ( sys-boot/gentool-bootcfg )
	conf? (
		sys-config/fragtoo-configs
		sys-config/fragtoo-configs-valve
	)
	dsp? ( media-sound/steamdeck-dsp )
	fan? ( sys-power/jupiter-fan-control )
	fkernel? ( >=sys-kernel/fragtoo-kernel-7.3.1 )
	gkernel? ( || ( sys-kernel/gentoo-kernel sys-kernel/gentoo-kernel-bin ) )
	hub? ( app-portage/fragtoo-hub )
	hw? ( sys-apps/fragtoo-hw-support )
	kconf? ( sys-kernel/fragtoo-kernel-config )
	menu? ( app-misc/gentool-menu )
	patches? ( sys-kernel/fragtoo-patches )
	ryzen? ( >=app-admin/ryzen_smu-0.1.5-r1 )
	scripts? ( app-portage/gentool-scripts )
	vkernel? ( sys-kernel/fragtoo-valve-kernel )
"
