EAPI=8
DESCRIPTION="Valve Steam Deck PipeWire/LV2 speaker and mic DSP processing"
HOMEPAGE="https://fragtoo.com"
SRC_URI="https://steamdeck-packages.steamos.cloud/archlinux-mirror/sources/jupiter-main/steamdeck-dsp-${PV}-1.src.tar.gz"
LICENSE="all-rights-reserved"
SLOT="0"
KEYWORDS="~amd64"
RESTRICT="mirror bindist"
BDEPEND="dev-vcs/git"
DEPEND="media-sound/faust media-libs/lv2 media-libs/ladspa-sdk dev-libs/boost"
RDEPEND="media-video/pipewire media-video/wireplumber"
src_unpack() { default; git clone "${WORKDIR}/steamdeck-dsp/valve-hardware-audio-processing" "${S}" || die; }
src_compile() { emake FAUSTINC="${EPREFIX}/usr/include/faust" FAUSTLIB="${EPREFIX}/usr/share/faust"; }
src_install() { emake DEST_DIR="${D}/" install; }
