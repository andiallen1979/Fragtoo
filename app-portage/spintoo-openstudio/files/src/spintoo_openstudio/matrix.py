import json
import os
import re
import tempfile
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any


class MatrixError(ValueError):
    pass


@dataclass(frozen=True)
class BuildVariant:
    name: str
    arch: str = "amd64"
    vcpus: int = 4
    memory_mib: int = 8192
    make_conf: str = ""
    package_use: str = ""
    accept_keywords: str = ""
    package_mask: str = ""
    package_unmask: str = ""
    package_env: str = ""
    package_license: str = ""
    patches: str = ""
    kernel_config: str = ""
    world_packages: str = ""
    targets: str = ""

    def validate(self) -> None:
        for field in fields(self):
            value = getattr(self, field.name)
            if field.name in {"vcpus", "memory_mib"}:
                if isinstance(value, bool) or not isinstance(value, int):
                    raise MatrixError(f"{field.name} must be an integer.")
            elif not isinstance(value, str):
                raise MatrixError(f"{field.name} must be text.")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 ._()\-]{0,62}", self.name):
            raise MatrixError("Variant names must be 1-63 safe characters and start with a letter or digit.")
        if not re.fullmatch(r"[A-Za-z0-9_+-]{1,32}", self.arch):
            raise MatrixError("Architecture must be a non-empty Gentoo architecture name.")
        if not 1 <= self.vcpus <= 256:
            raise MatrixError("vCPUs must be between 1 and 256.")
        if not 512 <= self.memory_mib <= 1_048_576:
            raise MatrixError("Memory must be between 512 and 1048576 MiB.")

    @classmethod
    def from_mapping(cls, value: Any) -> "BuildVariant":
        if not isinstance(value, dict):
            raise MatrixError("Each build variant must be a JSON object.")
        allowed = {field.name for field in fields(cls)}
        unknown = set(value) - allowed
        if unknown:
            raise MatrixError(f"Unknown variant field(s): {', '.join(sorted(unknown))}.")
        try:
            variant = cls(**value)
        except TypeError as exc:
            raise MatrixError(f"Invalid build variant: {exc}") from exc
        variant.validate()
        return variant


@dataclass
class BuildMatrix:
    variants: list[BuildVariant]

    def validate(self) -> None:
        if not self.variants:
            raise MatrixError("A build matrix must contain at least one variant.")
        names: set[str] = set()
        for variant in self.variants:
            variant.validate()
            normalized = variant.name.casefold()
            if normalized in names:
                raise MatrixError(f"Variant name '{variant.name}' is duplicated.")
            names.add(normalized)

    def to_mapping(self) -> dict[str, Any]:
        self.validate()
        return {"schema_version": 1, "variants": [asdict(item) for item in self.variants]}

    @classmethod
    def from_mapping(cls, value: Any) -> "BuildMatrix":
        if not isinstance(value, dict) or value.get("schema_version") != 1:
            raise MatrixError("Unsupported or invalid build matrix schema.")
        unknown = set(value) - {"schema_version", "variants"}
        if unknown:
            raise MatrixError(f"Unknown matrix field(s): {', '.join(sorted(unknown))}.")
        variants = value.get("variants")
        if not isinstance(variants, list):
            raise MatrixError("The build matrix 'variants' field must be a list.")
        matrix = cls([BuildVariant.from_mapping(item) for item in variants])
        matrix.validate()
        return matrix


def default_matrix_path() -> Path:
    config_home = os.environ.get("XDG_CONFIG_HOME")
    base = Path(config_home).expanduser() if config_home else Path.home() / ".config"
    return base / "spintoo-openstudio" / "matrix.json"


class MatrixStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or default_matrix_path()

    def load(self) -> BuildMatrix:
        if not self.path.exists():
            return BuildMatrix([BuildVariant(name="baseline")])
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise MatrixError(f"Could not read matrix '{self.path}': {exc}") from exc
        return BuildMatrix.from_mapping(raw)

    def save(self, matrix: BuildMatrix) -> None:
        payload = json.dumps(matrix.to_mapping(), indent=2) + "\n"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix=".matrix-", dir=self.path.parent)
        temp_path = Path(temp_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.chmod(temp_path, 0o600)
            os.replace(temp_path, self.path)
        finally:
            temp_path.unlink(missing_ok=True)
