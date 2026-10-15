#!/usr/bin/env python3
"""Project tool (S2-03b): one Langfuse project for each use case.

Runs in the backend image as the Compose tool service `langfuse-projects` (root; mounts the
project folder, the generated folder and /opt/langfuse/langfuse.env). Commands:
  add <use_case_id> --keys-file F          keys made in the Langfuse UI; checked first
  add unrouted --from-langfuse-env F       today's project keys from langfuse.env
  regenerate                               rewrite routes.yaml and projects.env
  list                                     use case, 8 characters of the public key, date
  routes --use-cases a,b --exporter file --file-dir D --output F   (CI routing test)
Never prints a full key. Exit 0 ok, 1 a check failed (nothing written), 2 usage.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import config, registry  # noqa: E402
from app import langfuse_projects as lp  # noqa: E402

Fetch = Callable[[str, str], tuple[int, bytes]]


def _fetch(url: str, auth: str) -> tuple[int, bytes]:
    request = urllib.request.Request(url, headers={"Authorization": auth,
                                                   "Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, b""


def _write(path: Path, text: str, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    fd = os.open(tmp, os.O_CREAT | os.O_TRUNC | os.O_WRONLY, mode)
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    os.chmod(tmp, mode)
    os.replace(tmp, path)


def _env_values(path: Path) -> dict[str, str]:
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        key, sep, value = line.strip().partition("=")
        if sep and not key.startswith("#"):
            values[key.strip()] = value.strip()
    return values


def _load_all(projects_dir: Path, registered: set[str]) -> list[lp.ProjectFile]:
    files = sorted(projects_dir.glob("*.yaml")) if projects_dir.exists() else []
    projects = [lp.parse_project(f.name, f.read_text(encoding="utf-8"), registered)
                for f in files]
    return lp.check_set(projects)


def _regenerate(projects_dir: Path, generated_dir: Path, registered: set[str]) -> list[str]:
    projects = _load_all(projects_dir, registered)        # raises before anything is written
    ids = [p.use_case_id for p in projects]
    _write(generated_dir / "routes.yaml", lp.render_routes(ids), 0o644)
    _write(generated_dir / "projects.env", lp.render_env(projects), 0o600)
    return ids


def _check_keys(base_url: str, use_case_id: str, public_key: str, secret_key: str,
                fetch: Fetch) -> None:
    auth = "Basic " + base64.b64encode(f"{public_key}:{secret_key}".encode()).decode()
    status, body = fetch(f"{base_url.rstrip('/')}/api/public/projects", auth)
    if status != 200:
        raise lp.ProjectError(f"Langfuse answered {status} for these keys")
    try:
        names = [p.get("name") for p in json.loads(body).get("data", [])]
    except (ValueError, AttributeError):
        raise lp.ProjectError("Langfuse answered with bad JSON") from None
    if names != [use_case_id]:
        raise lp.ProjectError(
            f"these keys belong to project {', '.join(map(str, names)) or '(none)'}, "
            f"not {use_case_id}; create the project with that exact name")


def _add(ns, registered: set[str], fetch: Fetch) -> int:
    projects_dir, uc = Path(ns.projects_dir), ns.use_case_id
    source = Path(ns.keys_file or ns.from_langfuse_env)
    try:
        values = _env_values(source)
    finally:
        if ns.keys_file:
            source.unlink(missing_ok=True)                 # the keys file never stays
    if ns.keys_file:
        pk, sk = values.get("LANGFUSE_PUBLIC_KEY", ""), values.get("LANGFUSE_SECRET_KEY", "")
    else:
        pk = values.get("LANGFUSE_INIT_PROJECT_PUBLIC_KEY", "")
        sk = values.get("LANGFUSE_INIT_PROJECT_SECRET_KEY", "")
    if not pk or not sk:
        raise lp.ProjectError(f"{source.name}: the public and the secret key are needed")
    if uc != lp.UNROUTED and uc not in registered:
        raise lp.ProjectError(f"use case {uc} is not in the registry")
    _check_keys(ns.langfuse_url, uc, pk, sk, fetch)
    text = (f"use_case_id: {uc}\npublic_key: {pk}\nsecret_key: {sk}\n"
            f"added_at: \"{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}\"\n")
    lp.parse_project(f"{uc}.yaml", text, registered)        # same rules as regenerate
    target = projects_dir / f"{uc}.yaml"
    previous = target.read_text(encoding="utf-8") if target.exists() else None
    projects_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(projects_dir, 0o700)
    _write(target, text, 0o600)
    try:
        ids = _regenerate(projects_dir, Path(ns.generated_dir), registered)
    except lp.ProjectError:
        if previous is None:                                # undo: nothing half-written
            target.unlink(missing_ok=True)
        else:
            _write(target, previous, 0o600)
        raise
    print(f"added {uc}; projects: {', '.join(ids)}")
    return 0


def _list(ns, registered: set[str]) -> int:
    for p in _load_all(Path(ns.projects_dir), registered):
        print(f"{p.use_case_id}\t{p.public_key[:8]}…\t{p.added_at}")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="langfuse_projects.py")
    parser.add_argument("--projects-dir", default="/projects")
    parser.add_argument("--generated-dir", default="/generated")
    parser.add_argument("--registry", default=config.BATCH_REGISTRY_PATH)
    parser.add_argument("--langfuse-url",
                        default=os.environ.get("LANGFUSE_URL", "http://langfuse-web:3000"))
    sub = parser.add_subparsers(dest="command", required=True)
    add = sub.add_parser("add")
    add.add_argument("use_case_id")
    source = add.add_mutually_exclusive_group(required=True)
    source.add_argument("--keys-file")
    source.add_argument("--from-langfuse-env")
    sub.add_parser("regenerate")
    sub.add_parser("list")
    routes = sub.add_parser("routes")
    routes.add_argument("--use-cases", required=True)
    routes.add_argument("--exporter", choices=["otlphttp", "file"], default="otlphttp")
    routes.add_argument("--file-dir", default="/out")
    routes.add_argument("--output", required=True)
    return parser


def main(argv: list[str] | None = None, *, fetch: Fetch | None = None) -> int:
    try:
        ns = _parser().parse_args(argv)
    except SystemExit:
        return 2
    try:
        if ns.command == "routes":
            ids = [x.strip() for x in ns.use_cases.split(",") if x.strip()]
            _write(Path(ns.output), lp.render_routes(ids, exporter=ns.exporter,
                                                     file_dir=ns.file_dir), 0o644)
            return 0
        registered = set(registry.load(ns.registry))
        if ns.command == "add":
            return _add(ns, registered, fetch or _fetch)
        if ns.command == "regenerate":
            ids = _regenerate(Path(ns.projects_dir), Path(ns.generated_dir), registered)
            print(f"regenerated; projects: {', '.join(ids)}")
            return 0
        return _list(ns, registered)
    except (lp.ProjectError, registry.RegistryError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"error: {type(exc).__name__} on a file", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
