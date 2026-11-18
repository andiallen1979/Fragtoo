EAPI=8
inherit cmake
DESCRIPTION="Functional programming language for real-time signal processing"
HOMEPAGE="https://grame.fr"
SRC_URI="https://github.com{PV}/faust-${PV}.tar.gz"
LICENSE="GPL-2+"
SLOT="0"
KEYWORDS="~amd64 ~arm64"
CMAKE_USE_DIR="${S}/build"

PATCHES=(
	"${FILESDIR}/fix-gcc16-cstdint.patch"
)

src_configure() {
	local mycmakeargs=(
		-DINCLUDE_EXECUTABLE=ON
		-DINCLUDE_STATIC=OFF
		-DINCLUDE_DYNAMIC=OFF
		-DINCLUDE_OSC=OFF
		-DINCLUDE_HTTP=OFF
		-DC_BACKEND=COMPILER
		-DCPP_BACKEND=COMPILER
	)
	cmake_src_configure
}
