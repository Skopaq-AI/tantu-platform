#!/usr/bin/env bash
# scripts/version.sh — Single source of truth for SemVer across TANTU platform
#
# Usage:
#   ./scripts/version.sh get                      # print current version from .version
#   ./scripts/version.sh bump patch|minor|major   # bump, sync all VERSION files, update pyproject.toml + package.json
#   ./scripts/version.sh bump patch --dry-run     # preview without writing
#   ./scripts/version.sh set 1.2.3                # set explicit version
#   ./scripts/version.sh sync                     # sync .version → services/*/VERSION + pyproject.toml + package.json
#   ./scripts/version.sh check                    # verify all VERSION files match .version
#
# CI usage:
#   VERSION=$(./scripts/version.sh get)
#   ./scripts/version.sh bump minor  # in release.yml after semver decision
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION_FILE="$ROOT/.version"
SERVICES=(adapter-fabric edge-perception reasoning-copilot orchestrator api-gateway)

SEMVER_RE='^[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.-]+)?(\+[0-9A-Za-z.-]+)?$'

die() { echo "error: $*" >&2; exit 1; }
info() { echo "[version.sh] $*" >&2; }

get_version() {
  [[ -f "$VERSION_FILE" ]] || die ".version not found at $VERSION_FILE"
  local v
  v="$(tr -d ' \t\n\r' < "$VERSION_FILE")"
  [[ "$v" =~ $SEMVER_RE ]] || die "invalid semver in .version: '$v'"
  printf '%s\n' "$v"
}

set_version() {
  local new_ver="$1"
  local dry_run="${2:-false}"
  [[ "$new_ver" =~ $SEMVER_RE ]] || die "invalid semver: '$new_ver' (expected X.Y.Z)"
  if [[ "$dry_run" == "true" ]]; then
    info "dry-run: would set version → $new_ver"
    return 0
  fi
  printf '%s\n' "$new_ver" > "$VERSION_FILE"
  info "root .version → $new_ver"
  for svc in "${SERVICES[@]}"; do
    local vf="$ROOT/services/$svc/VERSION"
    printf '%s\n' "$new_ver" > "$vf"
    info "services/$svc/VERSION → $new_ver"
  done
  # Sync pyproject.toml versions (hatchling: [project].version = "X.Y.Z")
  for svc in "${SERVICES[@]}"; do
    local pp="$ROOT/services/$svc/pyproject.toml"
    if [[ -f "$pp" ]]; then
      if grep -qE '^version = "' "$pp"; then
        python3 - "$pp" "$new_ver" <<'PY'
import re, sys
pp, ver = sys.argv[1], sys.argv[2]
with open(pp, 'r') as f:
    txt = f.read()
txt_new, n = re.subn(r'^(version\s*=\s*)"[^"]+"', r'\1"' + ver + '"', txt, count=1, flags=re.MULTILINE)
if n == 0:
    print(f"warn: no version field replaced in {pp}", file=sys.stderr)
else:
    with open(pp, 'w') as f:
        f.write(txt_new)
PY
        info "services/$svc/pyproject.toml → $new_ver"
      fi
    fi
  done
  local pkg="$ROOT/frontend/package.json"
  if [[ -f "$pkg" ]]; then
    python3 - "$pkg" "$new_ver" <<'PY'
import json, sys
pkg, ver = sys.argv[1], sys.argv[2]
with open(pkg) as f:
    data = json.load(f)
data["version"] = ver
with open(pkg, 'w') as f:
    json.dump(data, f, indent=2)
    f.write("\n")
PY
    info "frontend/package.json → $new_ver"
  fi
  if [[ -f "$ROOT/backend/pyproject.toml" ]]; then
    python3 - "$ROOT/backend/pyproject.toml" "$new_ver" <<'PY'
import re, sys
pp, ver = sys.argv[1], sys.argv[2]
import pathlib
p = pathlib.Path(pp)
txt = p.read_text()
txt_new, n = re.subn(r'^(version\s*=\s*)"[^"]+"', r'\1"' + ver + '"', txt, count=1, flags=re.MULTILINE)
if n:
    p.write_text(txt_new)
PY
  fi
  info "version set to $new_ver (synced ${#SERVICES[@]} services + frontend)"
}

bump_version() {
  local part="$1"
  local dry_run="${2:-false}"
  local cur
  cur="$(get_version)"
  local base="${cur%%-*}"; base="${base%%+*}"
  IFS='.' read -r major minor patch <<< "$base"
  case "$part" in
    major) major=$((major+1)); minor=0; patch=0 ;;
    minor) minor=$((minor+1)); patch=0 ;;
    patch) patch=$((patch+1)) ;;
    *) die "bump expects patch|minor|major, got '$part'" ;;
  esac
  local new_ver="${major}.${minor}.${patch}"
  set_version "$new_ver" "$dry_run"
  printf '%s\n' "$new_ver"
}

sync_versions() {
  local cur
  cur="$(get_version)"
  set_version "$cur" "false"
}

check_versions() {
  local cur
  cur="$(get_version)"
  local ok=true
  for svc in "${SERVICES[@]}"; do
    local vf="$ROOT/services/$svc/VERSION"
    if [[ ! -f "$vf" ]]; then
      echo "MISSING  services/$svc/VERSION" >&2; ok=false; continue
    fi
    local sv
    sv="$(tr -d ' \t\n\r' < "$vf")"
    if [[ "$sv" != "$cur" ]]; then
      echo "MISMATCH services/$svc/VERSION: $sv != $cur (.version)" >&2; ok=false
    else
      echo "OK       services/$svc/VERSION = $sv"
    fi
  done
  for svc in "${SERVICES[@]}"; do
    local pp="$ROOT/services/$svc/pyproject.toml"
    if [[ -f "$pp" ]]; then
      local pv
      pv="$(grep -E '^version = "' "$pp" | head -n1 | sed -E 's/.*"(.*)".*/\1/')"
      if [[ "$pv" != "$cur" ]]; then
        echo "MISMATCH services/$svc/pyproject.toml version: $pv != $cur" >&2; ok=false
      else
        echo "OK       services/$svc/pyproject.toml = $pv"
      fi
    fi
  done
  local pkg="$ROOT/frontend/package.json"
  if [[ -f "$pkg" ]]; then
    local fv
    fv="$(python3 -c "import json;print(json.load(open('$pkg'))['version'])")"
    if [[ "$fv" != "$cur" ]]; then
      echo "MISMATCH frontend/package.json: $fv != $cur" >&2; ok=false
    else
      echo "OK       frontend/package.json = $fv"
    fi
  fi
  if [[ "$ok" == "true" ]]; then
    echo "All versions synced at $cur"
  else
    die "version drift detected — run ./scripts/version.sh sync"
  fi
}

usage() {
  cat >&2 <<'USAGE'
Usage: scripts/version.sh <command> [args]

Commands:
  get                              Print current version from .version
  set <X.Y.Z> [--dry-run]          Set explicit semver and sync to all services
  bump <patch|minor|major> [--dry-run]  Bump version (SemVer) and sync
  sync                             Re-sync .version → services/*/VERSION + pyproject + package.json
  check                            Verify all VERSION files match .version

Examples:
  ./scripts/version.sh get
  ./scripts/version.sh bump patch
  ./scripts/version.sh set 1.2.3
  ./scripts/version.sh check
USAGE
  exit 1
}

cmd="${1:-}"
case "$cmd" in
  get) get_version ;;
  set)
    ver="${2:-}"; [[ -n "$ver" ]] || usage
    dry="false"; [[ "${3:-}" == "--dry-run" ]] && dry="true"
    set_version "$ver" "$dry"
    ;;
  bump)
    part="${2:-}"; [[ -n "$part" ]] || usage
    dry="false"; [[ "${3:-}" == "--dry-run" ]] && dry="true"
    bump_version "$part" "$dry"
    ;;
  sync) sync_versions ;;
  check) check_versions ;;
  *) usage ;;
esac
