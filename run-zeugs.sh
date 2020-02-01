#!/bin/bash
# This starts a gunicorn server for production purposes
PORT=5005

thisfile=$( realpath "$0"  )
thisdir=$( dirname "$thisfile" )
#export FLASK_ENV=development
export ZEUGS_BASE="$thisdir"
cd "$thisdir/zeugs"
#"$thisdir/venv/bin/python" -m flask run
"$thisdir/venv/bin/gunicorn" --workers=2 --bind=127.0.0.1:$PORT --worker-class=gthread --threads=2 "flask_app:create_app()"
