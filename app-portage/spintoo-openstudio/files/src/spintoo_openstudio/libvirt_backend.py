from dataclasses import dataclass


class VMBackendError(RuntimeError):
    pass


@dataclass(frozen=True)
class VMInfo:
    name: str
    uuid: str
    state: str
    active: bool


_STATE_NAMES = {
    0: "running",
    1: "blocked",
    2: "paused",
    3: "shutting down",
    4: "shut off",
    5: "crashed",
    6: "suspended",
}


def list_domains(uri: str = "qemu:///system") -> list[VMInfo]:
    try:
        import libvirt
    except ImportError as exc:
        raise VMBackendError("The libvirt Python bindings are not installed.") from exc

    try:
        connection = libvirt.openReadOnly(uri)
    except libvirt.libvirtError as exc:
        raise VMBackendError(f"Could not connect to {uri}: {exc}") from exc
    if connection is None:
        raise VMBackendError(f"Could not connect to {uri}; check libvirt and Polkit permissions.")

    try:
        result = []
        for domain in connection.listAllDomains(0):
            state = domain.state()[0]
            result.append(
                VMInfo(
                    name=domain.name(),
                    uuid=domain.UUIDString(),
                    state=_STATE_NAMES.get(state, f"unknown ({state})"),
                    active=bool(domain.isActive()),
                )
            )
        return sorted(result, key=lambda item: item.name.casefold())
    except libvirt.libvirtError as exc:
        raise VMBackendError(f"Could not read libvirt guests: {exc}") from exc
    finally:
        connection.close()
