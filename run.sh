#!/usr/bin/env sh

if [ -f "${CERT_FILE}" ] && [ -f "${KEY_FILE}" ]; then
    gunicorn -b "0.0.0.0:$PORT" main:app \
        -k uvicorn.workers.UvicornWorker -w 1 \
        --certfile="${CERT_FILE}" --keyfile="${KEY_FILE}"
else
    gunicorn -b "0.0.0.0:$PORT" main:app -k uvicorn.workers.UvicornWorker -w 1
fi
