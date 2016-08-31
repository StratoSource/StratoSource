"""
Django settings for ss2 project.

Generated by 'django-admin startproject' using Django 1.8.3.

For more information on this file, see
https://docs.djangoproject.com/en/1.8/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.8/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
import sys

PROJECT_PATH = os.path.abspath(os.path.split(__file__)[0])

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = '/var/sfrepo/config'

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.8/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '4hggxc2u+f#23&@0l+^$z5lq*8wyw1c*#c&cgee8q^vfm4l#6$'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = (
#    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'bootstrap3',
    'django.contrib.humanize',
    'stratosource',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.gzip.GZipMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',
)


#import warnings
#warnings.filterwarnings('error', r"DateTimeField .* received a naive datetime", RuntimeWarning, r'django\.db\.models\.fields')

ROOT_URLCONF = 'ss2.urls'


TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'stratosource', 'admin', 'templates'), os.path.join(BASE_DIR, 'stratosource', 'user', 'templates')]
        ,
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'ss2.wsgi.application'


# detect if running inside Docker
IN_CONTAINER = 'CONTAINERIZED' in os.environ

if IN_CONTAINER and 'dbhost' in os.environ:

    dbport = os.environ['dbport'] if 'dbport' in os.environ else ''
    dbeng = os.environ['dbengine'] if 'dbengine' in os.environ else 'mysql'
    DATABASES = {
        #'default': {
        #    'ENGINE': 'django.db.backends.sqlite3',
        #    'NAME': '/tmp/placeholder',
        #},
        'default': {
            'ENGINE': 'django.db.backends.' + dbeng, # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
            'NAME': 'stratosource',                      # Or path to database file if using sqlite3.
            'USER': 'stratosource',                      # Not used with sqlite3.
            'PASSWORD': 'stratosource',                  # Not used with sqlite3.
            'HOST': os.environ['dbhost'],
            'PORT': dbport
        }
    }

else:

    DATABASES = {
        #'default': {
        #    'ENGINE': 'django.db.backends.sqlite3',
        #    'NAME': '/tmp/placeholder',
        #},
        'default': {
            'ENGINE': 'django.db.backends.mysql', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
            'NAME': 'stratosource',                      # Or path to database file if using sqlite3.
            'USER': 'stratosource',                      # Not used with sqlite3.
            'PASSWORD': 'stratosource',                  # Not used with sqlite3.
    #        'HOST': '192.168.1.60',                      # Set to empty string for localhost. Not used with sqlite3.
            'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
            'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
            'OPTIONS': {
                'init_command': 'SET sql_mode=STRICT_TRANS_TABLES'
            }
        }
    }

#DATABASE_ROUTERS = ['ss2.dbrouter.SSRouter']

# Internationalization
# https://docs.djangoproject.com/en/1.8/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'America/New_York'

USE_I18N = True

USE_L10N = True

USE_TZ = False


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.8/howto/static-files/

STATIC_URL = '/static/'

RALLY_REST_VERSION = '1.36'
RALLY_SERVER = 'rally1.rallydev.com'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'stream': sys.stdout,
            'formatter': 'simple'
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'propagate': True,
        },
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': False,
        },
        'console': {
            'handlers': ['console'],
            'level': 'DEBUG'
        }
    }
}
