#!/usr/bin/env bash
# S2-03b, test host only: add a Langfuse project for a use case, or rebuild the routes.
#   sudo bash add-langfuse-project.sh <use_case_id> --keys-file <path>   keys from the Langfuse UI
#   sudo bash add-langfuse-project.sh unrouted --from-langfuse-env       today's project keys
#   sudo bash add-langfuse-project.sh --regenerate | --list
# The keys file needs LANGFUSE_PUBLIC_KEY= and LANGFUSE_SECRET_KEY=; it is deleted.
# Prints names only. Then restart the Collector and the backend (the command is printed).
set -euo pipefail
[ "$(id -u)" = "0" ] || { echo "run with sudo" >&2; exit 1; }
cd "$(dirname "$0")"
PROJECTS=/opt/model-monitor/langfuse-projects
GENERATED=/opt/model-monitor/langfuse-generated
install -d -m 700 "$PROJECTS"
install -d -m 755 "$GENERATED"
RUN=(docker compose -f compose.yaml -f compose.testhost.yaml --profile tools run --rm -T langfuse-projects)
usage() { sed -n '2,7p' "$0" >&2; exit 2; }
trap 'rm -f "$PROJECTS/.incoming.keys"' EXIT
case "${1:-}" in
  --regenerate) "${RUN[@]}" regenerate ;;
  --list) "${RUN[@]}" list; exit 0 ;;
  ""|-*) usage ;;
  *)
    UC="$1"; shift
    case "${1:-}" in
      --keys-file)
        SRC="${2:-}"
        [ -s "$SRC" ] || { echo "the keys file is missing or empty" >&2; exit 1; }
        install -m 600 "$SRC" "$PROJECTS/.incoming.keys"
        rm -f "$SRC"
        "${RUN[@]}" add "$UC" --keys-file /projects/.incoming.keys ;;
      --from-langfuse-env)
        "${RUN[@]}" add "$UC" --from-langfuse-env /langfuse.env ;;
      *) usage ;;
    esac ;;
esac
echo "Now restart: sudo docker compose -f compose.yaml -f compose.testhost.yaml up -d --force-recreate collector backend"
