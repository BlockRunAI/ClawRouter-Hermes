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

enable_plugin() {
  local py="$1"
  local bin_dir hermes_bin
  bin_dir="$(dirname "$py")"
  hermes_bin="$bin_dir/hermes"
  if [[ ! -x "$hermes_bin" ]]; then
    if have hermes; then
      hermes_bin="$(command -v hermes)"
    else
      warn "Hermes command not found; skipping 'hermes plugins enable $PLUGIN_NAME'."
      return 0
    fi
  fi

  if "$hermes_bin" plugins enable "$PLUGIN_NAME"; then
    log "Enabled Hermes plugin: $PLUGIN_NAME"
  else
    warn "Could not run 'hermes plugins enable $PLUGIN_NAME'. Continuing; setup still writes the provider config."
  fi
}

install_into_venv() {
  local py="$1"
  log "Installing $PKG_SPEC into Hermes environment: $py"
  "$py" -m ensurepip --upgrade >/dev/null 2>&1 || true
  "$py" -m pip install --upgrade pip wheel >/dev/null
  "$py" -m pip install --upgrade "$PKG_SPEC"
  enable_plugin "$py"
  run_clawrouter_cli "$py" setup
  log "Running doctor (warnings are OK if the wallet is not funded yet)..."
  run_clawrouter_cli "$py" doctor || true
}

install_with_pipx() {
  have pipx || return 1
  if ! pipx list --short 2>/dev/null | sed -n 's/[[:space:]].*$//p' | grep -qx 'hermes-agent'; then
    return 1
  fi
  log "Installing $PKG_SPEC into pipx Hermes app: hermes-agent"
  pipx inject --include-apps --force hermes-agent "$PKG_SPEC"
  if have hermes; then
    hermes plugins enable "$PLUGIN_NAME" || warn "Could not run 'hermes plugins enable $PLUGIN_NAME'."
  fi
  if have hermes-clawrouter; then
    hermes-clawrouter setup
    log "Running doctor (warnings are OK if the wallet is not funded yet)..."
    hermes-clawrouter doctor || true
  else
    warn "pipx did not expose hermes-clawrouter on PATH. Run 'pipx ensurepath', reopen your shell, then run 'hermes-clawrouter setup'."
  fi
}

main() {
  log "== ClawRouter for Hermes installer =="
  log "This installer avoids system pip and PEP 668 by installing into Hermes' own environment."

  local hermes_py
  if hermes_py="$(find_hermes_python)"; then
    install_into_venv "$hermes_py"
    log "Done. Restart Hermes, then choose blockrun/auto in /model."
    return 0
  fi

  if install_with_pipx; then
    log "Done. Restart Hermes, then choose blockrun/auto in /model."
    return 0
  fi

  if [[ -n "$BROKEN_HERMES_TARGET" ]]; then
    warn "Your 'hermes' launcher points to a missing file: $BROKEN_HERMES_TARGET"
  fi

  cat >&2 <<'EOF'

Could not find a working Hermes virtualenv to install into.

Fix Hermes first, then rerun this installer. Recommended beginner-safe path:

  sudo apt update && sudo apt install -y pipx
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
