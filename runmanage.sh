#!/bin/bash

#BASEDIR=$(dirname $0)
#cd "$BASEDIR/stratosource"
cd /usr/django

python manage.py "$@"
