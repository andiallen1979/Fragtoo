# Project Handoff: WakStab Host Binhost & `fragtoo` Gaming Overlay

## 1. Completed on Host (`WakStab` Overlay)
- **Overlay Location:** `/var/db/repos/WakStab` (`codeberg.org:andiallen1979/WakStab.git`).
- **Unified Portage Configurator (`app-misc/wakstabcfg-2.0.0`):**
  - `IUSE="+gui gtk3 gtk4 qt6"` (`-gui` acts as a master TUI-only override).
  - Ships `wakstabcfg` (Midnight Commander `modarin` default skin `ncurses` TUI with `F1`-`F10` bar, mouse support, scrollbars), `wakstabcfg-qt6`, `wakstabcfg-gtk3`, and `wakstabcfg-gtk4`.
  - Includes profile-locked (`*`) USE flag warnings, Pre-Save Sanity Check with core-mask/`**` risk escalation, non-root `./portage-preview/` fallback, and `genlop -t` slowest-build sorting.
- **QA Status:** Entire `WakStab` repo passes `pkgcheck scan` with zero errors/warnings and is pushed to Codeberg.

## 2. Current Active Step (Phase 1 — In Progress)
- Desktop host is running a full `wakstab-emptytree` build.
- **Next Action When `wakstab-emptytree` Finishes:**
  1. Inspect `/etc/portage/review/latest/audit.txt` and `/etc/portage/review/latest/genlop.txt`.
  2. Generate tailored `/etc/portage/env/*.conf` profiles (`SLOW_AF.conf`, `o3-perf.conf`, etc.) and `package.env` assignments.
  3. Remove global `ABI_X86="64 32"` from `/etc/portage/make.conf` and use `emerge -pv --changed-use --deep @world --autounmask-write && dispatch-conf` to keep `abi_x86_32` only on Steam/Wine/Heroic dependencies.

## 3. Next Planned Project (Phase 2 — `fragtoo` Overlay for Steam Deck LCD)
- **Repository:** `/var/db/repos/fragtoo` (gaming-focused Gentoo overlay, no `Wak` or `Deck` prefix).
- **Versioned Binhost Target:** `/var/cache/binpkgs/fragtoo/0.1.0` (`-march=znver2` for Steam Deck LCD AMD Van Gogh APU, 16 GB shared UMA RAM/VRAM).
- **Design Goals:**
  - Single-slot mutable Gentoo rootfs (no A/B recovery partitions, no `steamos-readonly` locks).
  - Unpack Valve's `steamdeck-recovery-*.img.bz2` to extract and package `gamescope-session` + `steamos-session-select` (Game Mode <-> Plasma 6.7 Desktop Mode switching), udev rules, polkit TDP/GPU/brightness helpers, and `steamdeck-dsp` PipeWire/WirePlumber profiles.
  - Lean Plasma 6.7 (`-baloo`, `-akonadi`, `-discover`), selective `-O3 -march=znver2` (`mesa`, `vulkan-loader`, `ffmpeg`, `zstd`), minimal per-package `abi_x86_32`, and `zram`.

## 4. Future Planned Project (Phase 3 — Motorola `minsk` `arm64`)
- Cross-compile Gentoo `arm64` (`aarch64-unknown-linux-gnu`) into `/var/cache/binpkgs/minsk/0.1.0` using extracted `boot.img` / DTS / firmware blobs and modular subsystem patches from Motorola's published GPL kernel tree.
