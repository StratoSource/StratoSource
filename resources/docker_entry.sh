#!/usr/bin/bash

chmod 777 /var/sfrepo /var/sftmp
# start apache httpd
apachectl

# wait forever
tail -f /dev/null
