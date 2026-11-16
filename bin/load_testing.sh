#!/bin/bash
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/ops-common.sh"
exec "${OPS_PYTHON:-python3}" "$EVS_OPS_HOME/bin/load_testing.py" "$@"
