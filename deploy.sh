#!/bin/bash
#
# TODO: Forking for deployment
#

LOG_NAME=/tmp/$1_$(date +%Y%M%d%H%M%S)_push.log
BASEDIR=$(dirname $0)
PUSH_ID = $1

# Execute function error() receiving ERROR or TERM signal
#
trap onexit INT ERR

function onexit()
{    
    cd $BASEDIR/stratosource >>$LOG_NAME 2>&1
    local exit_status=${1:-$?}
    
    echo Exiting with status $exit_status

    if [ $exit_status -eq "99" ]
        then
#        python manage.py storepushlog $PUSH_ID $LOG_NAME d
        exit 0
    fi
#    python manage.py storepushlog $PUSH_ID $LOG_NAME e
    exit $exit_status
    
    
}

cd $BASEDIR >>$LOG_NAME 2>&1

cd $BASEDIR/stratosource >>$LOG_NAME 2>&1

#python manage.py storepushlog $PUSH_ID $LOG_NAME r

cd $BASEDIR >>$LOG_NAME 2>&1

onexit 99
