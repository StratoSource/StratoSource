#!/bin/bash

BASEDIR=$(dirname $0)
cd "$BASEDIR/stratosource"

python3 manage.py "$@"
