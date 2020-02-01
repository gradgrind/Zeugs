#!/bin/bash

thisfile=$( realpath "$0"  )
thisdir=$( dirname "$thisfile" )
cd "$thisdir/zeugs"
"$thisdir/venv/bin/python" test_gui.py
