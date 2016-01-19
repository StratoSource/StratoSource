#!/bin/bash

BASEDIR=$(dirname $0)
cd $BASEDIR/stratosource

python manage.py $*
