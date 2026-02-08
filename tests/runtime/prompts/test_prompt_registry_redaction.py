from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


def _load_prompt_registry():
    module_path = (
        Path(__file__).resolve().parents[3]
        / "agents"
        / "runtime"
        / "prompts"
        / "prompt_registry.py"
    )
    spec = spec_from_file_location("prompt_registry", module_path)
    module = module_from_spec(spec)
    if spec.loader is None:
        raise RuntimeError("Unable to load prompt_registry module.")
    spec.loader.exec_module(module)
    return module


prompt_registry = _load_prompt_registry()
_apply_redaction = prompt_registry._apply_redaction


def test_apply_redaction_recurses_through_lists():
    payload = {
        "messages": [
            {"metadata": {"token": "secret-token", "other": "keep"}},
            {"metadata": {"token": "second-token"}},
        ],
        "user": {"email": "person@example.com"},
    }
    fields = {"messages.metadata.token", "user.email"}

    redacted = _apply_redaction(payload, fields, "mask")

    assert redacted["messages"][0]["metadata"]["token"] == "[REDACTED]"
    assert redacted["messages"][1]["metadata"]["token"] == "[REDACTED]"
    assert redacted["messages"][0]["metadata"]["other"] == "keep"
    assert redacted["user"]["email"] == "[REDACTED]"


def test_apply_redaction_matches_sensitive_keys_case_insensitively():
    payload = {
        "secrets": {"Password": "supersecret", "ToKeN": "token-value"},
        "credentials": [{"Api_Key": "abc123"}, {"api_key": "def456"}],
    }
    fields = {"secrets.password", "secrets.token", "credentials.api_key"}

    redacted = _apply_redaction(payload, fields, "mask")

    assert redacted["secrets"]["Password"] == "[REDACTED]"
    assert redacted["secrets"]["ToKeN"] == "[REDACTED]"
    assert redacted["credentials"][0]["Api_Key"] == "[REDACTED]"
    assert redacted["credentials"][1]["api_key"] == "[REDACTED]"
