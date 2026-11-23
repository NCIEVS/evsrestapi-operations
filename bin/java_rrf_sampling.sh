#!/bin/bash
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/ops-common.sh"
exec "${JAVA_HOME:+$JAVA_HOME/bin/}java" ${JAVA_OPTS:--Xmx4096M} -jar "$(ops_loader_jar)" rrfSample "$@"
