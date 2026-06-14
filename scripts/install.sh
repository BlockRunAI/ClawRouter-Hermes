#!/usr/bin/env bash
set -Eeuo pipefail

PKG_NAME="${HERMES_CLAWROUTER_PACKAGE:-hermes-plugin-clawrouter}"
PKG_SPEC="$PKG_NAME"
if [[ -n "${HERMES_CLAWROUTER_VERSION:-}" ]]; then
  PKG_SPEC="${PKG_NAME}==${HERMES_CLAWROUTER_VERSION}"
fi

PLUGIN_NAME="${HERMES_CLAWROUTER_PLUGIN_NAME:-clawrouter}"
BROKEN_HERMES_TARGET=""

log() { printf '%s\n' "$*"; }
warn() { printf 'WARN: %s\n' "$*" >&2; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
have() { command -v "$1" >/dev/null 2>&1; }

resolve_path() {
  if have readlink; then
    readlink -f "$1" 2>/dev/null || printf '%s\n' "$1"
  else
    printf '%s\n' "$1"
  fi
}

is_venv_python() {
  "$1" - <<'PY'
import sys
raise SystemExit(0 if sys.prefix != sys.base_prefix else 1)
PY
}

is_safe_python_target() {
  local py="$1"
  [[ -x "$py" ]] || return 1
  is_venv_python "$py" || return 1
}

wrapper_target_from_file() {
  local file="$1"
  local line target
  [[ -f "$file" ]] || return 1
  while IFS= read -r line; do
    case "$line" in
      *".hermes/hermes-agent/venv/bin/hermes"*)
        target="$(printf '%s\n' "$line" | sed -n 's#.*\(/[^[:space:]"'"'"']*\.hermes/hermes-agent/venv/bin/hermes\).*#\1#p')"
        if [[ -n "$target" ]]; then
          printf '%s\n' "$target"
          return 0
        fi
        ;;
    esac
  done < "$file"
  return 1
}

run_privileged() {
  if [[ "$(id -u)" -eq 0 ]]; then
    "$@"
  elif have sudo; then
    sudo "$@"
  else
    return 1
  fi
}

install_python_packages() {
  log "Installing Python prerequisites..."
  if have apt-get; then
    run_privileged apt-get update
    run_privileged apt-get install -y python3 python3-venv python3-pip
  elif have dnf; then
    run_privileged dnf install -y python3 python3-pip
  elif have yum; then
    run_privileged yum install -y python3 python3-pip
  elif have pacman; then
    run_privileged pacman -Sy --needed --noconfirm python python-pip
  elif have zypper; then
    run_privileged zypper --non-interactive install python3 python3-pip
  elif have apk; then
    run_privileged apk add --no-cache python3 py3-pip
  elif have brew; then
    brew install python
  else
    return 1
  fi
}

ensure_python_basics() {
  if ! have python3; then
    install_python_packages || return 1
  fi
  have python3 || return 1

  if ! python3 -m venv --help >/dev/null 2>&1; then
    install_python_packages || return 1
  fi

  if ! python3 -m pip --version >/dev/null 2>&1; then
    python3 -m ensurepip --upgrade >/dev/null 2>&1 || install_python_packages || return 1
  fi
}

install_pipx_package() {
  log "Installing pipx..."
  if have apt-get; then
    run_privileged apt-get update
    run_privileged apt-get install -y pipx
  elif have dnf; then
    run_privileged dnf install -y pipx
  elif have yum; then
    run_privileged yum install -y pipx
  elif have pacman; then
    run_privileged pacman -Sy --needed --noconfirm python-pipx
  elif have zypper; then
    run_privileged zypper --non-interactive install python3-pipx
  elif have apk; then
    run_privileged apk add --no-cache pipx || run_privileged apk add --no-cache py3-pipx
  elif have brew; then
    brew install pipx
  else
    return 1
  fi
}

ensure_pipx() {
  have pipx && return 0
  ensure_python_basics || return 1
  install_pipx_package || return 1
  have pipx || return 1
  pipx ensurepath >/dev/null 2>&1 || true
}

install_node_packages() {
  log "Installing Node.js/npm prerequisites..."
  if have apt-get; then
    run_privileged apt-get update
    run_privileged apt-get install -y nodejs npm
  elif have dnf; then
    run_privileged dnf install -y nodejs npm
  elif have yum; then
    run_privileged yum install -y nodejs npm
  elif have pacman; then
    run_privileged pacman -Sy --needed --noconfirm nodejs npm
  elif have zypper; then
    run_privileged zypper --non-interactive install nodejs npm
  elif have apk; then
    run_privileged apk add --no-cache nodejs npm
  elif have brew; then
    brew install node
  else
    return 1
  fi
}

node_major() {
  local v major
  v="$(node --version 2>/dev/null || true)"
  major="${v#v}"
  major="${major%%.*}"
  [[ "$major" =~ ^[0-9]+$ ]] || return 1
  printf '%s\n' "$major"
}

ensure_node_tooling() {
  local major
  if have node && have npm && have npx; then
    major="$(node_major || true)"
    if [[ -n "$major" && "$major" -ge 18 ]]; then
      return 0
    fi
    warn "Node.js is present but may be too old: $(node --version 2>/dev/null || printf unknown). ClawRouter needs Node 18+."
  fi

  install_node_packages || return 1

  if have node && have npm && have npx; then
    major="$(node_major || true)"
    if [[ -z "$major" ]]; then
      warn "Could not parse Node.js version: $(node --version 2>/dev/null || printf unknown). Install Node 18+ if setup fails."
    elif [[ "$major" -lt 18 ]]; then
      warn "Installed Node.js version is $(node --version 2>/dev/null || printf unknown); install Node 18+ if setup fails."
    fi
    return 0
  fi
  return 1
}

ensure_venv_pip() {
  local py="$1"
  if "$py" -m pip --version >/dev/null 2>&1; then
    return 0
  fi
  "$py" -m ensurepip --upgrade >/dev/null 2>&1 || true
  if "$py" -m pip --version >/dev/null 2>&1; then
    return 0
  fi
  die "Hermes Python has no pip/ensurepip: $py. Install the python3-venv/python3-pip package, then rerun this installer."
}

repair_broken_hermes_launcher() {
  local launcher target backup
  launcher="$HOME/.local/bin/hermes"
  if [[ -f "$launcher" ]] && target="$(wrapper_target_from_file "$launcher")" && [[ ! -x "$target" ]]; then
    backup="$launcher.broken.$(date +%Y%m%d%H%M%S)"
    mv "$launcher" "$backup"
    warn "Moved broken Hermes launcher to $backup"
    warn "It pointed to missing file: $target"
  fi
}

find_hermes_python() {
  local candidate hermes_path resolved hermes_dir target first interp

  if [[ -n "${HERMES_PYTHON:-}" ]]; then
    if is_safe_python_target "$HERMES_PYTHON"; then
      printf '%s\n' "$HERMES_PYTHON"
      return 0
    fi
    die "HERMES_PYTHON is set but is not an executable virtualenv Python: $HERMES_PYTHON"
  fi

  candidate="$HOME/.hermes/hermes-agent/venv/bin/python"
  if is_safe_python_target "$candidate"; then
    printf '%s\n' "$candidate"
    return 0
  fi

  if have hermes; then
    hermes_path="$(command -v hermes)"
    resolved="$(resolve_path "$hermes_path")"
    hermes_dir="$(dirname "$resolved")"

    candidate="$hermes_dir/python"
    if is_safe_python_target "$candidate"; then
      printf '%s\n' "$candidate"
      return 0
    fi

    if target="$(wrapper_target_from_file "$hermes_path")"; then
      if [[ -x "$target" ]]; then
        candidate="$(dirname "$target")/python"
        if is_safe_python_target "$candidate"; then
          printf '%s\n' "$candidate"
          return 0
        fi
      else
        BROKEN_HERMES_TARGET="$target"
      fi
    fi

    if [[ -f "$resolved" ]]; then
      IFS= read -r first < "$resolved" || true
      case "$first" in
        "#!"*python*)
          interp="${first#\#!}"
          interp="${interp%% *}"
          if is_safe_python_target "$interp"; then
            printf '%s\n' "$interp"
            return 0
          fi
          ;;
      esac
    fi
  fi

  return 1
}

run_clawrouter_cli() {
  local py="$1"
  local subcmd="$2"
  shift 2
  local bin_dir cli
  bin_dir="$(dirname "$py")"
  cli="$bin_dir/hermes-clawrouter"
  if [[ -x "$cli" ]]; then
    "$cli" "$subcmd" "$@"
  else
    "$py" -c 'import sys; from clawrouter_hermes.cli import main; main(sys.argv[1:])' "$subcmd" "$@"
  fi
}

enable_plugin_in_config() {
  local py="$1"
  "$py" - "$PLUGIN_NAME" <<'PY'
import os
import sys
from pathlib import Path

import yaml

plugin_name = sys.argv[1]
home = Path(os.environ.get("HERMES_HOME") or (Path.home() / ".hermes")).expanduser()
path = home / "config.yaml"
path.parent.mkdir(parents=True, exist_ok=True)

try:
    raw = path.read_text(encoding="utf-8") if path.exists() else ""
    cfg = yaml.safe_load(raw) if raw.strip() else {}
except Exception:
    cfg = {}

if not isinstance(cfg, dict):
    cfg = {}

plugins = cfg.setdefault("plugins", {})
if not isinstance(plugins, dict):
    plugins = {}
    cfg["plugins"] = plugins

enabled = plugins.get("enabled")
if not isinstance(enabled, list):
    enabled = []

if plugin_name not in enabled:
    enabled.append(plugin_name)
plugins["enabled"] = sorted(str(item) for item in enabled)

path.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
print(f"Enabled Hermes plugin in config: {plugin_name} ({path})")
PY
}

enable_plugin() {
  local py="$1"
  local bin_dir hermes_bin
  bin_dir="$(dirname "$py")"
  hermes_bin="$bin_dir/hermes"
  if [[ ! -x "$hermes_bin" ]]; then
    if have hermes; then
      hermes_bin="$(command -v hermes)"
    else
      warn "Hermes command not found; enabling plugin directly in config."
      enable_plugin_in_config "$py"
      return 0
    fi
  fi

  if "$hermes_bin" plugins enable "$PLUGIN_NAME"; then
    log "Enabled Hermes plugin: $PLUGIN_NAME"
  else
    warn "Hermes CLI could not enable entry-point plugin '$PLUGIN_NAME'; enabling it directly in config."
    enable_plugin_in_config "$py"
  fi
}

install_into_venv() {
  local py="$1"
  log "Installing $PKG_SPEC into Hermes environment: $py"
  ensure_venv_pip "$py"
  "$py" -m pip install --upgrade pip wheel >/dev/null
  "$py" -m pip install --upgrade "$PKG_SPEC"
  ensure_node_tooling || warn "Node/npm/npx not available; setup will still run, but ClawRouter proxy install may be deferred or fail."
  enable_plugin "$py"
  run_clawrouter_cli "$py" setup --force
  log "Running doctor (warnings are OK if the wallet is not funded yet)..."
  run_clawrouter_cli "$py" doctor || true
}

install_with_pipx() {
  local pipx_bin hermes_bin cli
  ensure_pipx || return 1
  if ! pipx list --short 2>/dev/null | sed -n 's/[[:space:]].*$//p' | grep -qx 'hermes-agent'; then
    log "Hermes is not installed under pipx; installing hermes-agent..."
    pipx install hermes-agent
  fi
  log "Installing $PKG_SPEC into pipx Hermes app: hermes-agent"
  pipx inject --include-apps --force hermes-agent "$PKG_SPEC"
  pipx ensurepath >/dev/null 2>&1 || true

  pipx_bin="$(pipx environment --value PIPX_HOME 2>/dev/null || true)"
  pipx_bin="${pipx_bin:-$HOME/.local/share/pipx}/venvs/hermes-agent/bin"
  hermes_bin="$pipx_bin/hermes"
  cli="$pipx_bin/hermes-clawrouter"

  enable_plugin "$pipx_bin/python"

  ensure_node_tooling || warn "Node/npm/npx not available; setup will still run, but ClawRouter proxy install may be deferred or fail."

  if [[ -x "$cli" ]]; then
    "$cli" setup --force
    log "Running doctor (warnings are OK if the wallet is not funded yet)..."
    "$cli" doctor || true
  elif have hermes-clawrouter; then
    hermes-clawrouter setup --force
    log "Running doctor (warnings are OK if the wallet is not funded yet)..."
    hermes-clawrouter doctor || true
  else
    warn "pipx did not expose hermes-clawrouter on PATH. Run 'pipx ensurepath', reopen your shell, then run 'hermes-clawrouter setup'."
  fi
}

main() {
  log "== ClawRouter for Hermes installer =="
  log "This installer avoids system pip and PEP 668 by installing into Hermes' own environment."
  log "It checks Python, pip/venv support, pipx, and Node/npm/npx before setup."

  local hermes_py
  if hermes_py="$(find_hermes_python)"; then
    install_into_venv "$hermes_py"
    log "Done. Restart Hermes, then choose blockrun/auto in /model."
    return 0
  fi

  repair_broken_hermes_launcher

  if install_with_pipx; then
    log "Done. Restart Hermes, then choose blockrun/auto in /model."
    return 0
  fi

  if [[ -n "$BROKEN_HERMES_TARGET" ]]; then
    warn "Your 'hermes' launcher points to a missing file: $BROKEN_HERMES_TARGET"
  fi

  cat >&2 <<'EOF'

Could not find a working Hermes virtualenv to install into.

The installer tried to install missing basics through your OS package manager,
but could not complete automatically.

Manual Debian/Ubuntu recovery path:

  sudo apt update && sudo apt install -y python3 python3-venv python3-pip pipx nodejs npm
  pipx ensurepath
  pipx install hermes-agent
  curl -fsSL https://raw.githubusercontent.com/BlockRunAI/ClawRouter-Hermes/main/scripts/install.sh | bash

If your distro does not package pipx, use its official install instructions:

  https://pipx.pypa.io/stable/installation/

If Hermes is installed in a custom venv, point the installer at it:

  HERMES_PYTHON=/path/to/hermes/venv/bin/python \
    curl -fsSL https://raw.githubusercontent.com/BlockRunAI/ClawRouter-Hermes/main/scripts/install.sh | bash

EOF
  exit 1
}

main "$@"
