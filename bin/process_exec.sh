#!/bin/bash
# Windows argv quoting differs between native Python and Git Bash. Read literal
# arguments from the supervisor's environment, then use Bash's own exec handling.
[[ "${EVS_OPS_EXEC_ARGC:-}" =~ ^[0-9]+$ ]] && ((EVS_OPS_EXEC_ARGC > 0)) || exit 2
args=()
for ((i=0; i<EVS_OPS_EXEC_ARGC; i++)); do
  name="EVS_OPS_EXEC_ARG_$i"
  args+=("${!name}")
  unset "$name"
done
unset EVS_OPS_EXEC_ARGC
exec "$BASH" "${args[@]}"
