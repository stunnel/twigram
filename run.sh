#!/usr/bin/env sh

PROCESS_COUNT=${PROCESS_COUNT:-1}

if [ -f "${CERT_FILE}" ] && [ -f "${KEY_FILE}" ]; then
    gunicorn -b "0.0.0.0:$PORT" main:app \
        -k uvicorn.workers.UvicornWorker -w "${PROCESS_COUNT}" \
        --certfile="${CERT_FILE}" --keyfile="${KEY_FILE}"
else
    gunicorn -b "0.0.0.0:$PORT" main:app -k uvicorn.workers.UvicornWorker -w "${PROCESS_COUNT}"
fi
