#!/bin/sh
set -eu
exec "$WEBOTS_HOME/webots-controller" --protocol=tcp \
    --ip-address="${EREBUS_SERVER:-host.docker.internal}" \
    --port="${EREBUS_CONTROLLER_PORT:-1234}" \
    --robot-name="${EREBUS_ROBOT_NAME:-Erebus_Bot}" /controller/controller.py
