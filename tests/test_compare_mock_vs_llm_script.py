"""Regression tests for the live-model comparison harness."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


def _load_compare_module():
    path = Path(__file__).resolve().parents[1] / "scripts" / "compare_mock_vs_llm.py"
    spec = importlib.util.spec_from_file_location("compare_mock_vs_llm", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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


def test_main_creates_the_output_directory_before_writing(monkeypatch, tmp_path) -> None:
    module = _load_compare_module()
    out_path = tmp_path / "missing" / "mock_vs_llm_comparison.json"
    raw_path = tmp_path / "missing" / "llm_raw_response.txt"
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
                        "message": {
                            "content": (
                                '[{"name":"gap","description":"risk",'
                                '"failure_coverage":0.5,"evidence":[],'
                                '"suggested_criterion":"check risk"}]'
                            )
                        },
                        "finish_reason": "stop",
                    }
                ]
            }

    class Client:
        def __init__(self, **_kwargs: object) -> None:
            return None

        def __enter__(self):
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def post(self, _url: str, json: dict) -> Response:
            assert json["model"] == "served/model"
            return Response()

    monkeypatch.setattr(module.httpx, "Client", Client)

    assert module.main() == 0
    assert raw_path.is_file()
    assert out_path.is_file()
