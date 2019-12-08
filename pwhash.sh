#!/bin/bash

thisfile=$( realpath "$0"  )
thisdir=$( dirname "$thisfile" )
"$thisdir/venv/bin/python" "$thisdir/zeugs/flask_app/auth/genpass.py" $*
