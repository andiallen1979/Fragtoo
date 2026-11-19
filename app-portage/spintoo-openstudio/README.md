# Spintoo OpenStudio

Spintoo OpenStudio is a generic Gentoo build-host application. This first
prototype establishes a separate build matrix, a CPU/RAM-aware queue planner,
a local-only OpenAI-compatible AI draft client, and read-only libvirt guest
inventory.

New matrices start from the bundled **Fragtoo Valve baseline**, with an
**Empty** preset available for scratch variants. The baseline targets
`app-misc/fragtoo-meta`, the distro's dependency entry point, and enables its
Valve-kernel and patch-set options in addition to the default Gentoo-plus-Valve
kernel. That meta-package pulls the Fragtoo config packages, tools, support
packages, and selected kernel dependencies. The preset also includes the
extracted profile's world packages, Valve Portage settings, and Steam Deck
kernel config fragments. Its patch notes follow the ebuild sources: the
Gentoo-style kernel ebuild derives its Valve delta by diffing the vanilla and
Valve source trees, while the Valve kernel ebuild builds the Valve source
directly. Patch contents are not duplicated in the preset.

Existing Gentoo profile catalogs can be imported as variants, existing
`make.conf`, package configuration, kernel config, and patch files can be
imported into a variant, and ebuilds can be discovered from a selected overlay
as build targets. Variants retain the Gentoo architecture, resource requests,
and per-build target/configuration data.

The local model receives only the explicitly selected variants and the goal
shown in the request preview. AI output is displayed as a draft and is never
applied automatically. Assistant endpoints are restricted to loopback; proxy
settings are bypassed and HTTP redirects are not followed. The application
does not run as root or write to `/etc/portage`.

The queue tab is currently a resource-budget preview only. This version does
not yet create Gentoo templates, clone guests, or execute builds. Those are
follow-up steps: create and install a template through a guided Gentoo ISO
workflow, then clone and schedule matrix jobs through libvirt. The queue
currently shows the top-level meta-package target; it does not resolve its
dependency graph or build those packages.
