from __future__ import annotations

from app.config import _resolve_build_sha


def test_explicit_git_sha_wins_over_all_deployment_identifiers(tmp_path):
    build_sha_file = tmp_path / ".build-sha"
    build_sha_file.write_text("source-file-sha\n", encoding="utf-8")

    assert _resolve_build_sha(
        {
            "GIT_SHA": "explicit-source-sha",
            "COMMIT_SHA": "generic-commit-sha",
            "REPLIT_DEPLOYMENT_SHA": "synthetic-replit-revision",
        },
        build_sha_file,
    ) == "explicit-source-sha"


def test_stamped_checkout_sha_wins_over_replit_deployment_revision(tmp_path):
    build_sha_file = tmp_path / ".build-sha"
    build_sha_file.write_text("github-checkout-sha\n", encoding="utf-8")

    assert _resolve_build_sha(
        {
            "COMMIT_SHA": "generic-commit-sha",
            "REPLIT_DEPLOYMENT_SHA": "synthetic-replit-revision",
        },
        build_sha_file,
    ) == "github-checkout-sha"


def test_replit_deployment_revision_is_only_a_final_compatibility_fallback(tmp_path):
    assert _resolve_build_sha(
        {"REPLIT_DEPLOYMENT_SHA": "synthetic-replit-revision"},
        tmp_path / "missing-build-sha",
    ) == "synthetic-replit-revision"


def test_missing_build_identifiers_report_unknown(tmp_path):
    assert _resolve_build_sha({}, tmp_path / "missing-build-sha") == "unknown"
