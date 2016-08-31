#!/usr/bin/bash

# start apache httpd
apachectl

# wait forever
tail -f /dev/null
