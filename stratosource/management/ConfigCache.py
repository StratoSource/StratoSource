#    Copyright 2010, 2011 Red Hat Inc.
#
#    This file is part of StratoSource.
#
#    StratoSource is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    StratoSource is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with StratoSource.  If not, see <http://www.gnu.org/licenses/>.
#    
from stratosource.models import ConfigSetting
from django.contrib.sessions.backends.db import SessionStore
from django.core.exceptions import ObjectDoesNotExist
import logging
import uuid

logger = logging.getLogger('console')

__author__="tkruger"
__date__ ="$Aug 12, 2011 10:33:31 AM$"

session = SessionStore()

def refresh():
    settings = {}
    setList = ConfigSetting.objects.all()
    for setting in setList:
        #logger.debug('Adding ' + setting.key)
        settings[setting.key] = setting.value
    session['settings'] = settings

def get_uuid():
    theid = get_config_value('uuid')
    if len(theid) == 0:
        theid = uuid.uuid1()
        store_config_value('uuid', theid)
    return theid

def get_config_value(key):
    if not 'settings' in session:
        #logger.debug('Refreshing cache')
        refresh()
    settings = session['settings']
    if key in settings:
        logger.debug('Returning ' + key)
        return settings[key]
    else:
        return ''

def store_config_value(key, value):
    try:
        setting = ConfigSetting.objects.get(key=key)
    except ObjectDoesNotExist:
        setting = ConfigSetting()
        setting.key = key

    setting.value = value
    setting.save()
    refresh()
