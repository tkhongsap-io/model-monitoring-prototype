#!/usr/bin/env bash
# Shared env for the Replit build/start scripts — source it, don't execute it:
#   source scripts/replit_env.sh
# Sets: ROOT (repo root), PY (venv python or empty), MPLBACKEND;
# on Nix, wires LD_LIBRARY_PATH for LightGBM/SHAP native libs if the loader
# can't already find them.

export MPLBACKEND="${MPLBACKEND:-Agg}"   # headless matplotlib (bake artifacts)

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

# --- venv python: RAI_VENV override -> root .venv (Replit) -> backend/.venv (local dev) ---
_venv_py() {
  if [ -x "$1/bin/python" ]; then echo "$1/bin/python"; return 0; fi
  if [ -x "$1/Scripts/python.exe" ]; then echo "$1/Scripts/python.exe"; return 0; fi
  return 1
}
# An explicit RAI_VENV override is authoritative — fail loudly rather than
# silently falling back to a different interpreter than the one demanded.
if [ -n "${RAI_VENV:-}" ] && ! _venv_py "$RAI_VENV" >/dev/null; then
  echo "[replit_env] ERROR: RAI_VENV=$RAI_VENV has no python" >&2
  return 1 2>/dev/null || exit 1
fi
PY=""
for _v in "${RAI_VENV:-}" "$ROOT/.venv" "$ROOT/backend/.venv"; do
  [ -n "$_v" ] || continue
  if PY="$(_venv_py "$_v")"; then break; fi
  PY=""
done
# PY may legitimately be empty mid-build (before the venv is created).

# --- native libs (Nix only): libgomp.so.1 / libstdc++.so.6 for LightGBM & SHAP ---
# replit.nix provides them; this only kicks in if the dynamic loader misses them.
if [ -d /nix/store ] && [ -n "$PY" ]; then
  if ! "$PY" -c "import ctypes; ctypes.CDLL('libstdc++.so.6'); ctypes.CDLL('libgomp.so.1')" >/dev/null 2>&1; then
    _cxx="$(find /nix/store -maxdepth 3 -name 'libstdc++.so.6' 2>/dev/null | head -n 1 || true)"
    _gomp="$(find /nix/store -maxdepth 3 -name 'libgomp.so.1' 2>/dev/null | head -n 1 || true)"
    _extra=""
    [ -n "$_cxx" ] && _extra="$(dirname -- "$_cxx")"
    [ -n "$_gomp" ] && _extra="${_extra:+$_extra:}$(dirname -- "$_gomp")"
    if [ -n "$_extra" ]; then
      export LD_LIBRARY_PATH="${_extra}${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
      echo "[replit_env] LD_LIBRARY_PATH += $_extra"
    fi
  fi
fi
:
