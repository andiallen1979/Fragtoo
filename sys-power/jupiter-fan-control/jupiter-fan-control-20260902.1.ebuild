EAPI=8
PYTHON_COMPAT=( python3_{12..15} )
inherit python-single-r1
DESCRIPTION="Valve Jupiter Steam Deck EC fan controller daemon"
HOMEPAGE="https://fragtoo.com"
SRC_URI="https://steamdeck-packages.steamos.cloud/archlinux-mirror/sources/jupiter-main/jupiter-fan-control-${PV}-1.src.tar.gz"
LICENSE="MIT"
SLOT="0"
KEYWORDS="~amd64"
REQUIRED_USE="${PYTHON_REQUIRED_USE}"
BDEPEND="dev-vcs/git"
RDEPEND="${PYTHON_DEPS} $(python_gen_cond_dep "dev-python/pyyaml[\${PYTHON_USEDEP}]")"
src_unpack() { default; git clone "${WORKDIR}/jupiter-fan-control/jupiter-fan-control" "${S}" || die; }
src_install() { rm -rf .git README.md pyproject.toml; cp -a . "${D}/" || die; }
