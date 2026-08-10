#!/bin/bash
set -e

export PYTHONPATH="/home/frappe/frappe-bench/apps:${PYTHONPATH}"

if [ -f "/docker/scripts/wait-for-db.sh" ]; then
    /docker/scripts/wait-for-db.sh
fi

exec "$@"