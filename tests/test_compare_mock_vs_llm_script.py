"""Regression tests for the live-model comparison harness."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


def _load_compare_module():
    path = Path(__file__).resolve().parents[1] / "scripts" / "compare_mock_vs_llm.py"
    spec = importlib.util.spec_from_file_location("compare_mock_vs_llm", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _gap_payload(count: int, *, duplicate_names: bool = False) -> str:
    return json.dumps(
        [
            {
                "name": "gap" if duplicate_names else f"gap-{index}",
                "description": f"risk-{index}",
                "failure_coverage": 0.5,
                "evidence": [],
                "suggested_criterion": f"check risk {index}",
            }
            for index in range(count)
        ]
    )


def _gap_payload_with_malformed_fourth_item() -> str:
    payload = json.loads(_gap_payload(3))
    payload.append({"name": "incomplete-gap"})
    return json.dumps(payload)


def _gap_payload_with_invalid_coverage() -> str:
    payload = json.loads(_gap_payload(3))
    payload[1]["failure_coverage"] = "not-a-number"
    return json.dumps(payload)


def _gap_payload_with_out_of_range_coverage() -> str:
    payload = json.loads(_gap_payload(3))
    payload[1]["failure_coverage"] = 1.5
    return json.dumps(payload)


def _gap_payload_with_extra_field() -> str:
    payload = json.loads(_gap_payload(3))
    payload[1]["unexpected"] = "not allowed"
    return json.dumps(payload)


def _gap_payload_with_string_evidence() -> str:
    payload = json.loads(_gap_payload(3))
    payload[1]["evidence"] = "must be a list"
    return json.dumps(payload)


def test_resolve_model_discovers_the_only_served_model() -> None:
    module = _load_compare_module()

    class Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"data": [{"id": "served/model"}]}

    class Client:
        requested_url = ""

        def get(self, url: str) -> Response:
            self.requested_url = url
            return Response()

    client = Client()
    model = module.resolve_model(client, "http://127.0.0.1:8888/v1", "")

    assert model == "served/model"
    assert client.requested_url == "http://127.0.0.1:8888/v1/models"


@pytest.mark.parametrize("model_id", [None, 123, {"nested": "value"}])
def test_resolve_model_rejects_non_string_model_ids(model_id: object) -> None:
    module = _load_compare_module()

    class Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"data": [{"id": model_id}]}

    class Client:
        def get(self, _url: str) -> Response:
            return Response()

    with pytest.raises(RuntimeError, match="model endpoint returned an invalid response"):
        module.resolve_model(Client(), "http://127.0.0.1:8888/v1", "")


@pytest.mark.parametrize(
    "malformed_entry",
    [None, 123, "served/model", {}, {"id": ""}, {"id": 123}],
)
def test_resolve_model_rejects_malformed_entries_beside_a_valid_model(
    malformed_entry: object,
) -> None:
    module = _load_compare_module()

    class Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"data": [{"id": "served/model"}, malformed_entry]}

    class Client:
        def get(self, _url: str) -> Response:
            return Response()

    with pytest.raises(RuntimeError, match="model endpoint returned an invalid response"):
        module.resolve_model(Client(), "http://127.0.0.1:8888/v1", "")


def test_normalize_base_url_rejects_embedded_credentials() -> None:
    module = _load_compare_module()

    with pytest.raises(ValueError, match="must not include credentials"):
        module.normalize_base_url("http://review-user:secret-marker@127.0.0.1:8888/v1")


@pytest.mark.parametrize(
    ("base_url", "message"),
    [
        ("http://127.0.0.1:8888/v1?api_key=secret-marker", "query or fragment"),
        ("http://127.0.0.1:8888/v1#secret-marker", "query or fragment"),
        ("http://127.0.0.1:8888/v1?", "query or fragment"),
        ("http://127.0.0.1:8888/v1#", "query or fragment"),
        ("http://127.0.0.1:8888/v1\x1b[31m", "control characters"),
        ("http://127.0.0.1:8888/v1\nforged-log-line", "control characters"),
        ("ftp://127.0.0.1/v1", "absolute HTTP"),
        ("127.0.0.1:8888/v1", "absolute HTTP"),
        ("http:///v1", "absolute HTTP"),
    ],
)
def test_normalize_base_url_rejects_output_taint(
    base_url: str, message: str
) -> None:
    module = _load_compare_module()

    with pytest.raises(ValueError, match=message) as exc_info:
        module.normalize_base_url(base_url)

    assert "secret-marker" not in str(exc_info.value)
    assert "forged-log-line" not in str(exc_info.value)


def test_normalize_base_url_suppresses_malformed_port_taint() -> None:
    module = _load_compare_module()

    with pytest.raises(ValueError, match="absolute HTTP") as exc_info:
        module.normalize_base_url("http://127.0.0.1:secret-marker/v1")

    assert "secret-marker" not in str(exc_info.value)
    assert exc_info.value.__cause__ is None


@pytest.mark.parametrize(
    "model_id",
    [
        "served/model\x1b[31m",
        "served/model\nforged",
        "\nserved/model",
        "served/model\n",
        "served/model\u202e",
        "x" * 257,
    ],
)
def test_resolve_model_rejects_unsafe_values_from_discovery(
    model_id: str,
) -> None:
    module = _load_compare_module()

    class Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"data": [{"id": model_id}]}

    class Client:
        def get(self, _url: str) -> Response:
            return Response()

    with pytest.raises(RuntimeError, match="model endpoint returned an invalid response"):
        module.resolve_model(Client(), "http://127.0.0.1:8888/v1", "")


@pytest.mark.parametrize(
    "configured_model",
    [
        "configured/model\x1b[31m",
        "configured/model\nforged",
        "\nconfigured/model",
        "configured/model\n",
        "configured/model\u202e",
        "x" * 257,
    ],
)
def test_resolve_model_rejects_unsafe_explicit_override(
    configured_model: str,
) -> None:
    module = _load_compare_module()

    class Client:
        def get(self, _url: str) -> None:
            raise AssertionError("explicit model override must not trigger discovery")

    with pytest.raises(ValueError, match="SMF_SWARM_EVAL_MODEL") as exc_info:
        module.resolve_model(Client(), "http://127.0.0.1:8888/v1", configured_model)

    assert "configured/model" not in str(exc_info.value)


def test_resolve_model_normalizes_plain_surrounding_spaces() -> None:
    module = _load_compare_module()

    class Client:
        def get(self, _url: str) -> None:
            raise AssertionError("explicit model override must not trigger discovery")

    assert (
        module.resolve_model(
            Client(), "http://127.0.0.1:8888/v1", "  configured/model  "
        )
        == "configured/model"
    )


@pytest.mark.parametrize("configured_model", ["\nconfigured/model", "configured/model\n"])
def test_main_rejects_edge_control_from_model_environment(
    monkeypatch, tmp_path, capsys, configured_model: str
) -> None:
    monkeypatch.setenv("SMF_SWARM_EVAL_MODEL", configured_model)
    module = _load_compare_module()
    out_path = tmp_path / "mock_vs_llm_comparison.json"
    raw_path = tmp_path / "llm_raw_response.txt"
    monkeypatch.setattr(module, "OUT", out_path)
    monkeypatch.setattr(module, "RAW", raw_path)

    class Client:
        def __init__(self, **_kwargs: object) -> None:
            return None

        def __enter__(self):
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def get(self, _url: str) -> None:
            raise AssertionError("tainted explicit model must not trigger discovery")

        def post(self, _url: str, json: dict) -> None:
            raise AssertionError("tainted explicit model must be rejected before POST")

    monkeypatch.setattr(module.httpx, "Client", Client)

    with pytest.raises(ValueError, match="SMF_SWARM_EVAL_MODEL"):
        module.main()

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
    assert not raw_path.exists()
    assert not out_path.exists()


def test_main_rejects_tainted_discovered_model_before_post_or_output(
    monkeypatch, tmp_path, capsys
) -> None:
    module = _load_compare_module()
    out_path = tmp_path / "mock_vs_llm_comparison.json"
    raw_path = tmp_path / "llm_raw_response.txt"
    monkeypatch.setattr(module, "OUT", out_path)
    monkeypatch.setattr(module, "RAW", raw_path)
    monkeypatch.setattr(module, "MODEL", "")

    class Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"data": [{"id": "served/model\x1b[31mforged"}]}

    class Client:
        def __init__(self, **_kwargs: object) -> None:
            return None

        def __enter__(self):
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def get(self, _url: str) -> Response:
            return Response()

        def post(self, _url: str, json: dict) -> None:
            raise AssertionError("tainted model must be rejected before POST")

    monkeypatch.setattr(module.httpx, "Client", Client)

    with pytest.raises(RuntimeError, match="model endpoint returned an invalid response"):
        module.main()

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
    assert not raw_path.exists()
    assert not out_path.exists()


def test_main_creates_the_output_directory_before_writing(monkeypatch, tmp_path) -> None:
    module = _load_compare_module()
    out_path = tmp_path / "missing" / "mock_vs_llm_comparison.json"
    raw_path = tmp_path / "missing" / "llm_raw_response.txt"
    monkeypatch.setattr(module, "OUT", out_path)
    monkeypatch.setattr(module, "RAW", raw_path)
    monkeypatch.setattr(module, "MODEL", "")

    class ModelResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"data": [{"id": "served/model"}]}

    class Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {
                "choices": [
                    {
                        "message": {"content": _gap_payload(3)},
                        "finish_reason": "stop",
                    }
                ]
            }

    class Client:
        def __init__(self, **kwargs: object) -> None:
            assert kwargs["trust_env"] is False
            assert kwargs["timeout"] == 180.0

        def __enter__(self):
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def get(self, url: str) -> ModelResponse:
            assert url == "http://spark-56bc:8888/v1/models"
            return ModelResponse()

        def post(self, url: str, json: dict) -> Response:
            assert url == "http://spark-56bc:8888/v1/chat/completions"
            assert json["model"] == "served/model"
            return Response()

    monkeypatch.setattr(module.httpx, "Client", Client)

    assert module.main() == 0
    assert raw_path.is_file()
    assert out_path.is_file()
    report = json.loads(out_path.read_text(encoding="utf-8"))
    assert report["model"] == "served/model"
    assert report["llm"]["error"] is None


@pytest.mark.parametrize(
    ("content", "expected_count"),
    [
        (_gap_payload(0), 0),
        (_gap_payload(1), 1),
        (_gap_payload(2), 2),
        (_gap_payload(4), 4),
        (_gap_payload(3, duplicate_names=True), 3),
        (json.dumps([{"name": f"gap-{index}"} for index in range(3)]), 0),
        (_gap_payload_with_malformed_fourth_item(), 3),
        (_gap_payload_with_invalid_coverage(), 3),
        (_gap_payload_with_out_of_range_coverage(), 3),
        (_gap_payload_with_extra_field(), 2),
        (_gap_payload_with_string_evidence(), 2),
        (_gap_payload(3) + " trailing prose", 3),
    ],
)
def test_main_fails_closed_unless_exactly_three_distinct_valid_gaps(
    monkeypatch, tmp_path, content: str, expected_count: int
) -> None:
    module = _load_compare_module()
    out_path = tmp_path / "mock_vs_llm_comparison.json"
    raw_path = tmp_path / "llm_raw_response.txt"
    monkeypatch.setattr(module, "OUT", out_path)
    monkeypatch.setattr(module, "RAW", raw_path)
    monkeypatch.setattr(module, "MODEL", "served/model")

    class Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {
                "choices": [
                    {
                        "message": {"content": content},
                        "finish_reason": "stop",
                    }
                ]
            }

    class Client:
        def __init__(self, **kwargs: object) -> None:
            assert kwargs["trust_env"] is False

        def __enter__(self):
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def get(self, _url: str) -> None:
            raise AssertionError("explicit override must not trigger discovery")

        def post(self, _url: str, json: dict) -> Response:
            assert json["model"] == "served/model"
            return Response()

    monkeypatch.setattr(module.httpx, "Client", Client)

    assert module.main() == 1
    report = json.loads(out_path.read_text(encoding="utf-8"))
    assert report["llm"]["n_gaps"] == expected_count
    assert report["llm"]["error"] == "expected_exactly_three_distinct_valid_gaps"
