"""One Langfuse project per use case (S2-03b): the pure module."""
from __future__ import annotations

import base64

import pytest
import yaml

from app import config
from app import langfuse_projects as lp

REG = {"rtr-fraud-validation", "GCP-UC-03", "a-b", "a.b", "uc.v2:x"}


def text(uc="rtr-fraud-validation", pk="pk-lf-1111", sk="sk-lf-2222", **extra) -> str:
    body = {"use_case_id": uc, "public_key": pk, "secret_key": sk,
            "added_at": "2026-10-15T08:00:00Z", **extra}
    return yaml.safe_dump(body)


def project(uc, pk="pk-lf-1111", sk="sk-lf-2222"):
    return lp.parse_project(f"{uc}.yaml", text(uc, pk, sk), REG)


def test_env_slug():
    assert lp.env_slug("rtr-fraud-validation") == "RTR_FRAUD_VALIDATION"
    assert lp.env_slug("uc.v2:x") == "UC_V2_X"
    assert lp.env_slug("unrouted") == "UNROUTED"


def test_parse_good_file():
    p = project("rtr-fraud-validation")
    assert (p.use_case_id, p.public_key, p.secret_key) == ("rtr-fraud-validation", "pk-lf-1111",
                                                           "sk-lf-2222")


def test_unknown_field_is_refused_without_values():
    with pytest.raises(lp.ProjectError) as exc:
        lp.parse_project("rtr-fraud-validation.yaml",
                         text(secret_kay="sk-lf-leak").replace("secret_key: sk-lf-2222\n", ""),
                         REG)
    message = str(exc.value)
    assert "secret_kay" in message and "sk-lf-leak" not in message and "sk-lf-2222" not in message


@pytest.mark.parametrize("name, body, words", [
    ("other.yaml", text(), ["file name", "rtr-fraud-validation.yaml"]),
    ("nope.yaml", text("nope"), ["not in the registry"]),
    ("rtr-fraud-validation.yaml", text(pk="pk-xx"), ["public_key"]),
    ("rtr-fraud-validation.yaml", text(sk="secret"), ["secret_key"]),
    ("rtr-fraud-validation.yaml", "use_case_id: [", ["not valid YAML"]),
])
def test_bad_files(name, body, words):
    with pytest.raises(lp.ProjectError) as exc:
        lp.parse_project(name, body, REG)
    for word in words:
        assert word in str(exc.value)


def test_unrouted_needs_no_registry_entry():
    assert project("unrouted").use_case_id == "unrouted"


def test_check_set_needs_unrouted_and_sorts():
    with pytest.raises(lp.ProjectError, match="unrouted.yaml is missing"):
        lp.check_set([project("rtr-fraud-validation")])
    ordered = lp.check_set([project("rtr-fraud-validation"), project("GCP-UC-03"),
                            project("unrouted")])
    assert [p.use_case_id for p in ordered] == ["unrouted", "GCP-UC-03", "rtr-fraud-validation"]


def test_slug_collision_is_refused():
    with pytest.raises(lp.ProjectError, match="A_B"):
        lp.check_set([project("unrouted"), project("a-b"), project("a.b")])


def test_routing_condition_order():
    c = lp.routing_condition("rtr-fraud-validation")
    assert c == (
        'resource.attributes["use.case.id"] == "rtr-fraud-validation"'
        ' or (resource.attributes["use.case.id"] == nil'
        ' and attributes["use_case_id"] == "rtr-fraud-validation")'
        ' or (resource.attributes["use.case.id"] == nil and attributes["use_case_id"] == nil'
        ' and resource.attributes["service.name"] == "rtr-fraud-validation")')


def test_render_routes_otlphttp():
    doc = yaml.safe_load(lp.render_routes(["unrouted", "rtr-fraud-validation"]))
    routing = doc["connectors"]["routing/langfuse"]
    assert routing["default_pipelines"] == ["traces/langfuse-unrouted"]
    assert routing["error_mode"] == "ignore"
    assert [r["pipelines"] for r in routing["table"]] == [["traces/langfuse-rtr-fraud-validation"]]
    assert routing["table"][0]["context"] == "span"
    assert routing["table"][0]["condition"] == lp.routing_condition("rtr-fraud-validation")
    exp = doc["exporters"]["otlphttp/langfuse-rtr-fraud-validation"]
    assert exp == {"endpoint": "http://langfuse-web:3000/api/public/otel",
                   "headers": {"Authorization": "Basic ${env:LANGFUSE_OTLP_AUTH__RTR_FRAUD_VALIDATION}",
                               "x-langfuse-ingestion-version": "4"}}
    assert "otlphttp/langfuse-unrouted" in doc["exporters"]
    pipes = doc["service"]["pipelines"]
    assert pipes["traces/langfuse-unrouted"] == {"receivers": ["routing/langfuse"],
                                                 "exporters": ["otlphttp/langfuse-unrouted"]}
    assert lp.render_routes(["unrouted", "rtr-fraud-validation"]).startswith("# Generated")


def test_render_routes_file_mode_for_ci():
    doc = yaml.safe_load(lp.render_routes(["unrouted", "rtr-fraud-validation"],
                                          exporter="file", file_dir="/out"))
    assert doc["exporters"]["file/langfuse-rtr-fraud-validation"] == {
        "path": "/out/rtr-fraud-validation.jsonl"}
    assert doc["exporters"]["file/langfuse-unrouted"] == {"path": "/out/unrouted.jsonl"}


def test_ids_with_dots_and_colons():
    doc = yaml.safe_load(lp.render_routes(["unrouted", "uc.v2:x"]))
    assert "otlphttp/langfuse-uc.v2:x" in doc["exporters"]
    assert "LANGFUSE_OTLP_AUTH__UC_V2_X" in doc["exporters"]["otlphttp/langfuse-uc.v2:x"][
        "headers"]["Authorization"]


def test_render_env():
    env = lp.render_env(lp.check_set([project("unrouted", "pk-lf-u", "sk-lf-u"),
                                      project("rtr-fraud-validation", "pk-lf-r", "sk-lf-r")]))
    lines = [l for l in env.splitlines() if l and not l.startswith("#")]
    assert lines == [
        "LANGFUSE_PROJECTS=unrouted,rtr-fraud-validation",
        "LANGFUSE_PK__UNROUTED=pk-lf-u", "LANGFUSE_SK__UNROUTED=sk-lf-u",
        "LANGFUSE_OTLP_AUTH__UNROUTED=" + base64.b64encode(b"pk-lf-u:sk-lf-u").decode(),
        "LANGFUSE_PK__RTR_FRAUD_VALIDATION=pk-lf-r", "LANGFUSE_SK__RTR_FRAUD_VALIDATION=sk-lf-r",
        "LANGFUSE_OTLP_AUTH__RTR_FRAUD_VALIDATION=" + base64.b64encode(b"pk-lf-r:sk-lf-r").decode(),
    ]
    assert env.startswith("# Generated")


def test_keys_from_env_with_projects():
    env = {"LANGFUSE_PROJECTS": "unrouted, rtr-fraud-validation",
           "LANGFUSE_PK__UNROUTED": "pk-u", "LANGFUSE_SK__UNROUTED": "sk-u",
           "LANGFUSE_PK__RTR_FRAUD_VALIDATION": "pk-r", "LANGFUSE_SK__RTR_FRAUD_VALIDATION": "sk-r"}
    assert lp.keys_from_env(env, ("pk-old", "sk-old")) == {
        "unrouted": ("pk-u", "sk-u"), "rtr-fraud-validation": ("pk-r", "sk-r")}


def test_keys_from_env_fallback_is_unrouted():
    assert lp.keys_from_env({}, ("pk-old", "sk-old")) == {"unrouted": ("pk-old", "sk-old")}
    assert lp.keys_from_env({}, ("", "")) == {}


def test_keys_for_falls_back_to_unrouted():
    keys = {"unrouted": ("pk-u", "sk-u"), "rtr-fraud-validation": ("pk-r", "sk-r")}
    assert lp.keys_for(keys, "rtr-fraud-validation") == ("rtr-fraud-validation", ("pk-r", "sk-r"))
    assert lp.keys_for(keys, "GCP-UC-03") == ("unrouted", ("pk-u", "sk-u"))
    assert lp.keys_for(keys, None) == ("unrouted", ("pk-u", "sk-u"))
    assert lp.keys_for({"rtr-fraud-validation": ("pk-r", "sk-r")}, "other") is None


def test_config_langfuse_project_keys(monkeypatch):
    monkeypatch.delenv("LANGFUSE_PROJECTS", raising=False)
    monkeypatch.setattr(config, "LANGFUSE_PUBLIC_KEY", "pk-old")
    monkeypatch.setattr(config, "LANGFUSE_SECRET_KEY", "sk-old")
    assert config.langfuse_project_keys() == {"unrouted": ("pk-old", "sk-old")}
    monkeypatch.setenv("LANGFUSE_PROJECTS", "unrouted")
    monkeypatch.setenv("LANGFUSE_PK__UNROUTED", "pk-u")
    monkeypatch.setenv("LANGFUSE_SK__UNROUTED", "sk-u")
    assert config.langfuse_project_keys() == {"unrouted": ("pk-u", "sk-u")}
