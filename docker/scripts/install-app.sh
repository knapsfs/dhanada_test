#!/bin/bash
set -e

APP_NAME=$1

echo "Installing ${APP_NAME}..."

if [ -d "apps/${APP_NAME}" ]; then
    echo "Registering locally mounted ${APP_NAME}..."
    bench pip install -e "apps/${APP_NAME}"

    if ! grep -q "^${APP_NAME}$" sites/apps.txt; then
        echo "${APP_NAME}" >> sites/apps.txt
    fi
else
    echo "Fetching ${APP_NAME}..."
    bench get-app "${APP_NAME}"
fi

echo "Installing ${APP_NAME} on site ${SITE_NAME}..."
bench --site "${SITE_NAME}" install-app "${APP_NAME}" || true