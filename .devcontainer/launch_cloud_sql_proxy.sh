#!/bin/bash

PROXY_BIN="$(command -v cloud-sql-proxy || echo /cloud-sql-proxy)"

"$PROXY_BIN" "${INSTANCE_CONNECTION_NAME}" --address "127.0.0.1" --port 5432 &
sleep 5
