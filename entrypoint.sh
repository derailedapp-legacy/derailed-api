#!/bin/sh

exec gunicorn -w $((`nproc` * 2 + 1)) -k "uvicorn.workers.UvicornWorker" -b "0.0.0.0:5000" "app:app"
