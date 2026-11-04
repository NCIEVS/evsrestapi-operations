#!/bin/bash
#
# Script to set max_result_window for evs_metadata to 300000
#

if [ -n "$ES_SCHEME" ] && [ -n "$ES_HOST" ] && [ -n "$ES_PORT" ]; then
    echo "  Set max result window to 300000 for evs_mappings"
    echo "  ES = $ES_SCHEME://$ES_HOST:$ES_PORT"
    curl -s -X PUT "$ES_SCHEME://$ES_HOST:$ES_PORT/evs_mappings/_settings" \
         -H "Content-type: application/json" -d '{ "index" : { "max_result_window" : 300000 } }' >> /dev/null
    if [[ $? -ne 0 ]]; then
        echo "ERROR: unexpected error setting max_result_window for evs_mappings"
        exit 1
    fi

else
    echo "ERROR: environment variable not set"
    echo "  ES_SCHEME = $ES_SCHEME"
    echo "  ES_HOST = $ES_HOST"
    echo "  ES_PORT = $ES_PORT"
    exit 1
fi

