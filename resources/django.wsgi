import os
import sys

sys.path.append('/usr/django')

os.environ['DJANGO_SETTINGS_MODULE'] = 'stratosource.settings'

import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()

