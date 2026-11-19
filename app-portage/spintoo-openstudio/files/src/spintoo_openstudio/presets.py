import json
import re
from dataclasses import asdict, dataclass
from importlib.resources import files

from .matrix import BuildMatrix, BuildVariant, MatrixError


@dataclass(frozen=True)
class VariantPreset:
    preset_id: str
    description: str
    variant: BuildVariant


def load_builtin_presets() -> tuple[VariantPreset, ...]:
    try:
        raw = json.loads(files("spintoo_openstudio").joinpath("presets.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MatrixError(f"Could not load built-in variant presets: {exc}") from exc
    if not isinstance(raw, dict) or raw.get("schema_version") != 1:
        raise MatrixError("The built-in preset catalog has an unsupported schema.")
    if set(raw) != {"schema_version", "presets"} or not isinstance(raw["presets"], list):
        raise MatrixError("The built-in preset catalog must contain only a 'presets' list.")

    presets = []
    seen_ids = set()
    for index, value in enumerate(raw["presets"], start=1):
        if not isinstance(value, dict) or set(value) != {"id", "description", "variant"}:
            raise MatrixError(f"Built-in preset {index} has an invalid shape.")
        preset_id = value["id"]
        description = value["description"]
        if (
            not isinstance(preset_id, str)
            or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,62}", preset_id)
            or preset_id in seen_ids
            or not isinstance(description, str)
            or not description.strip()
        ):
            raise MatrixError(f"Built-in preset {index} has an invalid ID or description.")
        seen_ids.add(preset_id)
        presets.append(VariantPreset(
            preset_id=preset_id,
            description=description,
            variant=BuildVariant.from_mapping(value["variant"]),
        ))
    if not presets:
        raise MatrixError("The built-in preset catalog is empty.")
    return tuple(presets)


def default_matrix() -> BuildMatrix:
    presets = load_builtin_presets()
    baseline = next((preset for preset in presets if preset.preset_id == "fragtoo-valve-baseline"), None)
    if baseline is None:
        raise MatrixError("The built-in Fragtoo Valve baseline preset is missing.")
    return BuildMatrix([BuildVariant.from_mapping(asdict(baseline.variant))])
