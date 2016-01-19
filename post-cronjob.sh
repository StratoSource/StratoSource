
##
# Place any custom postprocessing here after the snapshot is processed
# arg1 is the repo name
# arg2 is the branch name
##
#cd /var/sfrepo/code
#git push origin $2:$2

#git --git-dir=/var/sfrepo/$2/code/.git push origin $2:$2
#git --git-dir=/var/sfrepo/$2/code/.git push /var/sfrepo/code/ $2:$2
python notify.py "Snapshot finished for $1:$2"
