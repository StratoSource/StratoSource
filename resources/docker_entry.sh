#!/usr/bin/bash

# Sleep 30 seconds to wait for db
sleep 30
python /usr/django/manage.py migrate

# start apache httpd
apachectl
# wait forever
tail -f /var/log/httpd/error_log -f /var/log/httpd/access_log
