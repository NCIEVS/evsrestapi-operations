#!/bin/bash
# Shared bootstrap for active mutating workflows. Preserve inherited environments in --noconfig mode.
EVS_OPS_HOME="${EVS_OPS_HOME:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)}"
export EVS_OPS_HOME
export PYTHONUTF8="${PYTHONUTF8:-1}"
# Only the API service launcher (bin/evsrestapi-operations) needs ADMIN_KEY. Drop it everywhere
# else, including after setenv.sh is loaded, so scripts and the tools they run never see it.
ops_drop_admin_key() { [[ "${_OPS_ADMIN_SERVICE:-}" == 1 ]] || unset ADMIN_KEY; }
ops_drop_admin_key
ops_use_bash() {
  local selected_bash="${OPS_BASH:-$BASH}"
  # Native Windows Python must not resolve bare bash to the WSL launcher on PATH.
  if [[ "$selected_bash" == bash || "$selected_bash" == bash.exe ]]; then
    selected_bash="$BASH"
  fi
  if command -v cygpath >/dev/null 2>&1; then
    selected_bash="$(cygpath -am -- "$selected_bash")" || return 1
    if [[ "$selected_bash" != *.exe && -f "$selected_bash.exe" ]]; then
      selected_bash="$selected_bash.exe"
    fi
  fi
  export OPS_BASH="$selected_bash"
}
ops_use_bash || exit 1
ops_use_java_home() {
  if [[ -n "${JAVA_HOME:-}" ]]; then
    local java_bin="$JAVA_HOME/bin"
    if command -v cygpath >/dev/null 2>&1; then
      java_bin="$(cygpath -u "$java_bin")"
    fi
    export PATH="$java_bin:$PATH"
  fi
}
ops_use_java_home
if [[ "$(head -n 1 "$0")" == *'bash -f'* ]]; then set -f; fi
# Path of the existing setenv.sh (it may not exist).
ops_config_file() {
  local app_home="${APP_HOME:-/local/content/evsrestapi}"
  if [[ -n "${OPS_CONFIG_ENV_FILE:-}" ]]; then
    printf '%s\n' "$OPS_CONFIG_ENV_FILE"
  elif [[ -n "${APP_NAME:-}" && -f "$app_home/$APP_NAME/config/setenv.sh" ]]; then
    printf '%s\n' "$app_home/$APP_NAME/config/setenv.sh"
  else
    printf '%s\n' "$app_home/config/setenv.sh"
  fi
}
# Resolve the existing configuration once per shell, before selecting the lock directory.
ops_load_config() {
  local required=${1:-0}
  if [[ "${_OPS_CONFIG_INITIALIZED:-0}" != 1 ]]; then
    local config_file
    config_file="$(ops_config_file)"
    CONFIG_ENV_FILE="$config_file"
    CONFIG_DIR="$(dirname -- "$config_file")"
    if [[ -f "$config_file" ]]; then
      source "$config_file" || return 1
      _OPS_CONFIG_LOADED=1
    fi
    export OPS_CONFIG_ENV_FILE="$config_file"
    _OPS_CONFIG_INITIALIZED=1
  fi
  ops_drop_admin_key
  CONFIG_ENV_FILE="$OPS_CONFIG_ENV_FILE"
  CONFIG_DIR="$(dirname -- "$CONFIG_ENV_FILE")"
  if [[ "$required" == 1 && "${_OPS_CONFIG_LOADED:-0}" != 1 ]]; then
    echo "ERROR: $CONFIG_ENV_FILE does not exist; use --noconfig for the caller's environment" >&2
    return 1
  fi
  ops_use_java_home
}
ops_lock() {
  local no_config=0 arg
  for arg in "$@"; do
    [[ "$arg" == "--help" || "$arg" == "-h" ]] && return 0
    [[ "$arg" == "--noconfig" ]] && no_config=1
  done
  if [[ "$no_config" == 0 ]]; then
    ops_load_config || exit 1
  fi
  ops_supervise "$@"
}
# For scripts that use only the caller's environment (devreset.sh, load.sh): take just
# OPS_STATE_DIR from setenv.sh, so the lock is shared without importing anything else.
ops_lock_caller_env() {
  local arg config_file state_dir
  for arg in "$@"; do
    [[ "$arg" == "--help" || "$arg" == "-h" ]] && return 0
  done
  config_file="$(ops_config_file)"
  if [[ -z "${OPS_STATE_DIR:-}" && -f "$config_file" ]]; then
    state_dir="$(source "$config_file" >/dev/null 2>&1; printf '%s' "${OPS_STATE_DIR:-}")"
    [[ -z "$state_dir" ]] || export OPS_STATE_DIR="$state_dir"
  fi
  ops_supervise "$@"
}
ops_supervise() {
  ops_use_bash || exit 1
  ops_use_java_home
  export OPS_STATE_DIR="${OPS_STATE_DIR:-$EVS_OPS_HOME/var}"
  # The supervisor verifies inherited lock tokens before allowing nested scripts.
  if [[ -z "${EVS_OPS_LOCK_TOKEN:-}" ]] || ! "${OPS_PYTHON:-python3}" "$EVS_OPS_HOME/bin/process_supervisor.py" --check-lock; then
    unset EVS_OPS_LOCK_TOKEN
    exec "${OPS_PYTHON:-python3}" "$EVS_OPS_HOME/bin/process_supervisor.py" -- "${OPS_BASH:-bash}" "$0" "$@"
  fi
}
ops_loader_jar() {
  if [[ -n "${EVS_LOADER_JAR:-}" ]]; then
    printf '%s\n' "$EVS_LOADER_JAR"
  elif [[ -f "$EVS_OPS_HOME/lib/evsrestapi-loader.jar" ]]; then
    printf '%s\n' "$EVS_OPS_HOME/lib/evsrestapi-loader.jar"
  else
    printf '%s\n' "$EVS_OPS_HOME/web/build/libs/evsrestapi-loader.jar"
  fi
}
# --help validates the executable and Java version without starting Spring or touching backends.
ops_require_loader() {
  ops_use_java_home
  local jar="$(ops_loader_jar)" output
  if [[ ! -r "$jar" ]]; then
    echo "ERROR: loader JAR not found: $jar; run make build in evsrestapi-operations" \
      "(or ./gradlew loaderJar in its web/ directory)" >&2
    return 1
  fi
  if ! output=$(java -jar "$jar" --help 2>&1); then
    echo "ERROR: loader preflight failed; the loader needs Java 25 (set JAVA_HOME in setenv.sh)" >&2
    printf '%s\n' "$output" >&2
    return 1
  fi
}
