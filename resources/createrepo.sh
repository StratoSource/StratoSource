#!/bin/bash

#
# Sample script to create a new repo and branch
# 

#
# Default to a known location. Changing this requires other config changes.  You are on your own.
# Perhaps a symlink will do?
#
BASEDIR=/var/sfrepo
if [ "$1" = ""]; then
  echo "usage: $0 branch_name"
  exit 0
fi

if [ ! -d $BASEDIR ]; then
  echo "$BASEDIR directory not found"
  exit 1
fi

NAME=$1

cd $BASEDIR
mkdir $NAME
cd $NAME
git init code
cd code
touch .gitignore
git add .gitignore
git commit -m "initial commit"
git checkout -b $NAME master
chown -R apache:apache $BASEDIR/$NAME
