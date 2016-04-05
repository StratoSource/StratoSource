import os
import sys

sys.path.append('/usr/django')

os.environ['DJANGO_SETTINGS_MODULE'] = 'ss2.settings'

#import django.core.handlers.wsgi
#application = django.core.handlers.wsgi.WSGIHandler()

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

