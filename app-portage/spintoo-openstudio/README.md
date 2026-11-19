# Spintoo OpenStudio

Spintoo OpenStudio is a generic Gentoo build-host application. This first
prototype establishes a separate build matrix, a CPU/RAM-aware queue planner,
a local-only OpenAI-compatible AI draft client, and read-only libvirt guest
inventory.

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
workflow, then clone and schedule matrix jobs through libvirt.
