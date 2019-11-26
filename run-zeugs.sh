#!/bin/bash

#thisfile=$( realpath "$0"  )
#thisdir=$( dirname "$thisfile" )

#. "$thisdir/venv/bin/activate"

#cd "$(dirname "$0")"
#. venv/bin/activate
#cd zeugs/flask

#export FLASK_APP=zeugs
#export FLASK_ENV=development

#flask run

thisfile=$( realpath "$0"  )
thisdir=$( dirname "$thisfile" )
#export FLASK_APP=zeugs
export FLASK_APP=flask_app
export FLASK_ENV=development
export ZEUGS_BASE="$thisdir"
#cd "$thisdir/zeugs/flask"
cd "$thisdir/zeugs"
"$thisdir/venv/bin/python" -m flask run
