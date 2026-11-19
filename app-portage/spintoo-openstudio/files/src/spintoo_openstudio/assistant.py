import json
from dataclasses import asdict, dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

from .matrix import BuildMatrix, BuildVariant, MatrixError


class AssistantError(ValueError):
    pass


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, new_url):
        return None


@dataclass(frozen=True)
class MatrixDraft:
    summary: str
    variants: list[BuildVariant]

    def to_mapping(self) -> dict:
        return {"summary": self.summary, "variants": [asdict(item) for item in self.variants]}


def validate_local_endpoint(base_url: str) -> str:
    try:
        parsed = urlsplit(base_url.strip())
        parsed.port
    except ValueError as exc:
        raise AssistantError(f"Invalid local endpoint URL: {exc}") from exc
    if parsed.scheme not in {"http", "https"} or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise AssistantError("For privacy, the AI endpoint must be a local HTTP(S) service.")
    if parsed.username or parsed.password:
        raise AssistantError("Credentials must not be embedded in the AI endpoint URL.")
    if parsed.query or parsed.fragment:
        raise AssistantError("Query strings and fragments are not allowed in the AI endpoint URL.")
    return base_url.strip().rstrip("/") + "/"


def build_request_payload(goal: str, variants: list[BuildVariant], model: str) -> dict:
    if not goal.strip():
        raise AssistantError("Enter what you want the local model to compare or propose.")
    if not model.strip():
        raise AssistantError("Enter the model name served by your local endpoint.")
    matrix = BuildMatrix(list(variants))
    matrix.validate()
    selected_context = json.dumps([asdict(item) for item in variants], indent=2)
    return {
        "model": model.strip(),
        "temperature": 0.2,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a Gentoo build-matrix assistant. Return only a JSON object with "
                    "'summary' (string) and 'variants' (array of complete variant objects). "
                    "A variant has name, arch, vcpus, memory_mib, make_conf, package_use, "
                    "accept_keywords, package_mask, package_unmask, package_env, package_license, "
                    "patches, kernel_config, world_packages, and targets. Never claim to apply changes."
                ),
            },
            {
                "role": "user",
                "content": f"Goal:\n{goal.strip()}\n\nSelected variants only:\n{selected_context}",
            },
        ],
    }


def parse_matrix_draft(content: str) -> MatrixDraft:
    raw = content.strip()
    if raw.startswith("```"):
        raw = raw.partition("\n")[2].removesuffix("```").strip()
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AssistantError(f"The model response is not valid JSON: {exc}") from exc
    if not isinstance(value, dict) or not isinstance(value.get("summary"), str):
        raise AssistantError("The model response must include a string 'summary'.")
    variants_value = value.get("variants")
    if not isinstance(variants_value, list):
        raise AssistantError("The model response must include a 'variants' list.")
    try:
        matrix = BuildMatrix([BuildVariant.from_mapping(item) for item in variants_value])
        matrix.validate()
    except MatrixError as exc:
        raise AssistantError(f"The model returned invalid variant data: {exc}") from exc
    return MatrixDraft(summary=value["summary"], variants=matrix.variants)


class LocalAssistant:
    def __init__(self, base_url: str, model: str, timeout: float = 90) -> None:
        self.base_url = validate_local_endpoint(base_url)
        self.model = model
        self.timeout = timeout

    def draft(self, goal: str, variants: list[BuildVariant]) -> MatrixDraft:
        payload = build_request_payload(goal, variants, self.model)
        endpoint = urljoin(self.base_url, "chat/completions")
        request = Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        opener = build_opener(ProxyHandler({}), _NoRedirect())
        try:
            with opener.open(request, timeout=self.timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            try:
                detail = exc.read(2048).decode("utf-8", errors="replace")
            finally:
                exc.close()
            raise AssistantError(f"Local model request failed with HTTP {exc.code}: {detail}") from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise AssistantError(f"Could not reach the local model endpoint: {exc}") from exc
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise AssistantError(f"The local model endpoint returned invalid JSON: {exc}") from exc

        try:
            content = result["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise AssistantError("The local model response has no chat-completion content.") from exc
        if not isinstance(content, str):
            raise AssistantError("The local model response content must be text.")
        return parse_matrix_draft(content)
