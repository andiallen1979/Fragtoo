# Copyright 2026 Gentoo Authors
# Distributed under the terms of the GNU General Public License v2
EAPI=8
DESCRIPTION="Meta-package for fragtoo Steam Deck gaming configuration and utilities"
HOMEPAGE="https://fragtoo.com"
LICENSE="metapackage"
SLOT="0"
KEYWORDS="amd64 ~amd64"
IUSE="+bootcfg +conf +kconf +scripts menu"
RDEPEND="
	bootcfg? ( sys-boot/gentool-bootcfg )
	menu? ( app-misc/gentool-menu )
	conf? ( sys-config/fragtoo-configs )
	kconf? ( sys-kernel/fragtoo-kernel-config )
	scripts? ( app-portage/gentool-scripts )
"
