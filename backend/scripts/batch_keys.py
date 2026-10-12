#!/usr/bin/env python3
"""S2-01: manage the API key entries of the batch jobs (BATCH_API_KEY_SHA256).

    batch_keys.py make   --use-case ID --key-out KEY_FILE --hash-out HASH_FILE   (laptop)
    batch_keys.py add    --env-file ENV --hash-file HASH_FILE                    (VM, sudo)
    batch_keys.py list   --env-file ENV
    batch_keys.py remove --env-file ENV --use-case ID --hash-prefix PREFIX

The key goes only to KEY_FILE (then to GCP Secret Manager); the monitor keeps only its
SHA-256. No output contains a key or more than 8 characters of a hash. Standard library
only, so it runs on the laptop and on the VM host. Restart the backend after add/remove.
Exit 0: done; 1: refused; 2: usage error.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import secrets
import stat
import sys
import tempfile
from pathlib import Path

ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
DIGEST = re.compile(r"^[0-9a-f]{64}$")
PREFIX = re.compile(r"^[0-9a-f]{8,64}$")
NAME = "BATCH_API_KEY_SHA256"


class Refused(Exception):
    """A refused action: the message is safe to print."""


def _private_write(path: Path, text: str) -> None:
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(text)


def _entries(value: str) -> list[str]:
    return [entry.strip() for entry in value.split(",") if entry.strip()]


def _parse(entry: str) -> tuple[str, str] | None:
    use_case_id, _, digest = entry.rpartition(":")
    use_case_id, digest = use_case_id.strip(), digest.strip().lower()
    if ID.match(use_case_id) and DIGEST.match(digest):
        return use_case_id, digest
    return None


def _read_env(path: Path) -> tuple[list[str], int | None]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        raise Refused(f"cannot read {path}") from None
    index = next((i for i, line in enumerate(lines) if line.startswith(f"{NAME}=")), None)
    return lines, index


def _write_env(path: Path, lines: list[str]) -> None:
    mode = stat.S_IMODE(path.stat().st_mode)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".batch_keys-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def make(args: argparse.Namespace) -> None:
    key_out, hash_out = Path(args.key_out), Path(args.hash_out)
    if key_out.resolve() == hash_out.resolve():
        raise Refused("key and hash output paths must differ; nothing written")
    for path in (key_out, hash_out):
        if path.exists():
            raise Refused(f"{path} exists; nothing written")
    key = secrets.token_urlsafe(32)
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    _private_write(key_out, key)
    _private_write(hash_out, f"{args.use_case}:{digest}\n")
    print(f"wrote key to {key_out} and hash line to {hash_out}")


def add(args: argparse.Namespace) -> None:
    env, hash_file = Path(args.env_file), Path(args.hash_file)
    try:
        entry = hash_file.read_text(encoding="utf-8").strip()
    except OSError:
        raise Refused(f"cannot read {hash_file}") from None
    parsed = _parse(entry)
    if parsed is None or "\n" in entry:
        raise Refused(f"{hash_file} does not contain one USE_CASE_ID:<64 hex> line")
    use_case_id, digest = parsed
    lines, index = _read_env(env)
    current = _entries(lines[index].split("=", 1)[1]) if index is not None else []
    if any((_parse(e) or ("", ""))[1] == digest for e in current):
        raise Refused("this key hash is already in the env file; nothing changed")
    value = ", ".join(current + [f"{use_case_id}:{digest}"])
    if index is None:
        lines.append(f"{NAME}={value}")
    else:
        lines[index] = f"{NAME}={value}"
    _write_env(env, lines)
    hash_file.unlink()
    print(f"added a key for {use_case_id} ({digest[:8]})")


def list_keys(args: argparse.Namespace) -> None:
    lines, index = _read_env(Path(args.env_file))
    current = _entries(lines[index].split("=", 1)[1]) if index is not None else []
    for position, entry in enumerate(current, start=1):
        parsed = _parse(entry)
        print(f"{parsed[0]} {parsed[1][:8]}" if parsed else f"#{position} malformed")


def remove(args: argparse.Namespace) -> None:
    env = Path(args.env_file)
    prefix = args.hash_prefix.lower()
    lines, index = _read_env(env)
    if index is None:
        raise Refused(f"{NAME} is not in the env file; nothing removed")
    current = _entries(lines[index].split("=", 1)[1])
    matches = [i for i, entry in enumerate(current)
               if (p := _parse(entry)) and p[0] == args.use_case and p[1].startswith(prefix)]
    if len(matches) != 1:
        raise Refused(f"{len(matches)} keys match; nothing removed")
    del current[matches[0]]
    lines[index] = f"{NAME}={', '.join(current)}"
    _write_env(env, lines)
    print(f"removed a key for {args.use_case} ({prefix[:8]})")


def _use_case(value: str) -> str:
    if not ID.match(value):
        raise argparse.ArgumentTypeError("not a valid use case ID")
    return value


def _prefix(value: str) -> str:
    if not PREFIX.match(value.lower()):
        raise argparse.ArgumentTypeError("8 to 64 hex characters")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="batch_keys.py", description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("make")
    p.add_argument("--use-case", required=True, type=_use_case)
    p.add_argument("--key-out", required=True)
    p.add_argument("--hash-out", required=True)
    p.set_defaults(func=make)
    p = sub.add_parser("add")
    p.add_argument("--env-file", required=True)
    p.add_argument("--hash-file", required=True)
    p.set_defaults(func=add)
    p = sub.add_parser("list")
    p.add_argument("--env-file", required=True)
    p.set_defaults(func=list_keys)
    p = sub.add_parser("remove")
    p.add_argument("--env-file", required=True)
    p.add_argument("--use-case", required=True, type=_use_case)
    p.add_argument("--hash-prefix", required=True, type=_prefix)
    p.set_defaults(func=remove)
    args = parser.parse_args(argv)
    try:
        args.func(args)
    except Refused as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1
    except OSError:
        print("refused: cannot complete file operation", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
