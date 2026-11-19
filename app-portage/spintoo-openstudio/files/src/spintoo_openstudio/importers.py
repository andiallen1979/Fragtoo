import json
import re
import shlex
from pathlib import Path
from typing import Any

from .matrix import BuildVariant, MatrixError


class ImportError(ValueError):
    pass


def _lines(value: Any, field: str, profile_id: str) -> str:
    if value is None:
        return ""
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ImportError(f"Profile '{profile_id}' field '{field}' must be a list of strings.")
    return "\n".join(value)


def _render_make_conf(value: Any, profile_id: str) -> str:
    if value is None:
        return ""
    if not isinstance(value, dict):
        raise ImportError(f"Profile '{profile_id}' field 'make_conf' must be an object.")
    lines = []
    for key, raw in value.items():
        if not isinstance(key, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key) or not isinstance(raw, str):
            raise ImportError(f"Profile '{profile_id}' has an invalid make.conf entry.")
        lines.append(f"{key}={shlex.quote(raw)}")
    return "\n".join(lines)


def import_profile_catalog(path: Path) -> list[BuildVariant]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ImportError(f"Could not read profile catalog '{path}': {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("profiles"), list):
        raise ImportError("Profile catalog must contain a 'profiles' list.")

    variants = []
    for index, profile in enumerate(data["profiles"], start=1):
        if not isinstance(profile, dict):
            raise ImportError(f"Profile {index} must be a JSON object.")
        profile_id = profile.get("id", f"profile-{index}")
        name = profile.get("name") or profile_id
        if not isinstance(profile_id, str) or not isinstance(name, str):
            raise ImportError(f"Profile {index} must have text 'id' and 'name' fields.")
        try:
            variant = BuildVariant(
                name=name,
                arch=profile.get("arch", "amd64"),
                make_conf=_render_make_conf(profile.get("make_conf"), profile_id),
                package_use=_lines(profile.get("package_use"), "package_use", profile_id),
                accept_keywords=_lines(profile.get("package_keywords"), "package_keywords", profile_id),
                package_mask=_lines(profile.get("package_mask"), "package_mask", profile_id),
                package_unmask=_lines(profile.get("package_unmask"), "package_unmask", profile_id),
                package_env=_lines(profile.get("package_env"), "package_env", profile_id),
                package_license=_lines(profile.get("package_license"), "package_license", profile_id),
                kernel_config=profile.get("kernel_config", ""),
                world_packages=_lines(profile.get("world_packages"), "world_packages", profile_id),
            )
            variant.validate()
        except MatrixError as exc:
            raise ImportError(f"Profile '{profile_id}' is invalid: {exc}") from exc
        if not isinstance(variant.kernel_config, str):
            raise ImportError(f"Profile '{profile_id}' field 'kernel_config' must be text.")
        variants.append(variant)
    if not variants:
        raise ImportError("Profile catalog contains no profiles.")
    return variants


def _package_name_from_ebuild(filename: str) -> str | None:
    match = re.fullmatch(r"(.+)-([0-9].*)\.ebuild", filename)
    return match.group(1) if match else None


def import_overlay_targets(root: Path) -> list[str]:
    if not root.is_dir():
        raise ImportError(f"Overlay directory '{root}' does not exist.")
    targets: set[str] = set()
    try:
        for category in sorted(root.iterdir()):
            if not category.is_dir() or category.name.startswith("."):
                continue
            for package in sorted(category.iterdir()):
                if not package.is_dir() or package.name in {"files", "metadata", "profiles"}:
                    continue
                if any(package.glob("*.ebuild")):
                    targets.add(f"{category.name}/{package.name}")
            for ebuild in category.glob("*.ebuild"):
                package_name = _package_name_from_ebuild(ebuild.name)
                if package_name:
                    targets.add(f"{category.name}/{package_name}")
    except OSError as exc:
        raise ImportError(f"Could not scan overlay '{root}': {exc}") from exc
    if not targets:
        raise ImportError(f"No ebuild targets were found under '{root}'.")
    return sorted(targets)


def import_config_files(paths: list[Path]) -> dict[str, str]:
    if not paths:
        raise ImportError("Select at least one configuration file.")
    suffix_fields = {
        ".use": "package_use",
        ".keywords": "accept_keywords",
        ".accept_keywords": "accept_keywords",
        ".mask": "package_mask",
        ".unmask": "package_unmask",
        ".env": "package_env",
        ".license": "package_license",
        ".config": "kernel_config",
    }
    imported: dict[str, list[str]] = {}
    for path in paths:
        if not path.is_file():
            raise ImportError(f"Configuration file '{path}' does not exist.")
        name = path.name.lower()
        if name.startswith("make.conf"):
            field = "make_conf"
        elif path.suffix.lower() in {".patch", ".diff"}:
            field = "patches"
        else:
            field = suffix_fields.get(path.suffix.lower())
        if not field:
            raise ImportError(f"Do not know how to import '{path.name}'.")
        try:
            contents = str(path.resolve()) if field == "patches" else path.read_text(encoding="utf-8")
        except OSError as exc:
            raise ImportError(f"Could not read '{path}': {exc}") from exc
        imported.setdefault(field, []).append(contents.rstrip("\n"))
    return {field: "\n".join(contents for contents in values if contents) for field, values in imported.items()}
