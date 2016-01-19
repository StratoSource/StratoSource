#!/bin/bash
#
# Script invoked by cron to process a snapshot
# arg1 is the repo name
# arg2 is the branch name
#

LOG_NAME=/tmp/$1_$2_$(date +%Y%M%d%H%M%S)_pull.log
BASEDIR=$(dirname $0)
REPO=$1
BRANCH=$2

# Execute function error() receiving ERROR or TERM signal
#
trap onexit INT ERR

function onexit()
{    
    cd $BASEDIR >>$LOG_NAME 2>&1
    local exit_status=${1:-$?}
    
    echo Exiting with status $exit_status

    if [ $exit_status -eq "99" ]
        then
        python manage.py storelog $REPO $BRANCH $LOG_NAME d
        exit 0
    fi
    python manage.py storelog $REPO $BRANCH $LOG_NAME e
    exit $exit_status
    
    
}

echo Starting Code Snapshot of $REPO $BRANCH >>$LOG_NAME 2>&1

cd $BASEDIR >>$LOG_NAME 2>&1
./pre-cronjob.sh $REPO $BRANCH config >>$LOG_NAME 2>&1

python manage.py storelog $REPO $BRANCH $LOG_NAME config r

python manage.py download $REPO $BRANCH config >>$LOG_NAME 2>&1
python manage.py storelog $REPO $BRANCH $LOG_NAME config r

python manage.py commit  $REPO $BRANCH config >>$LOG_NAME 2>&1
python manage.py storelog $REPO $BRANCH $LOG_NAME config r

python manage.py sfdiff $REPO $BRANCH >>$LOG_NAME 2>&1
python manage.py storelog $REPO $BRANCH $LOG_NAME config r

cd $BASEDIR >>$LOG_NAME 2>&1
./post-cronjob.sh $REPO $BRANCH config >>$LOG_NAME 2>&1

rm $LOG_NAME

onexit 99
