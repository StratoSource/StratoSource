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
from stratosource.admin.models import ConfigSetting
from django.core.exceptions import ObjectDoesNotExist
import uuid

STANDARDCHKSETTINGS='rally.enabled,agilezen.enabled'
STANDARDTXTSETTINGS='rally.login,email.host,email.from'
STANDARDPASSWORDS='rally.password,agilezen.apikey'

s = ConfigSetting(key='calendar.host', value='localhost', allow_delete=False, masked=False)
s.save()
s = ConfigSetting(key='uuid',value=uuid.uuid1(), allow_delete=False, masked=False)
s.save()

for name in STANDARDTXTSETTINGS.split(','):
  s = ConfigSetting(key=name, value='', allow_delete=False, masked=False)
  s.save()

for name in STANDARDCHKSETTINGS.split(','):
  s = ConfigSetting(key=name, value='', type='check', allow_delete=False, masked=False)
  s.save()

for name in STANDARDPASSWORDS.split(','):
  s = ConfigSetting(key=name, value='', allow_delete=False, masked=True)
  s.save()
  

#try:
#    unReleased = Release.objects.get(name='Unreleased')
#    unReleased.name = 'Unreleased'
#    unReleased.hidden = True
#    unReleased.isdefault = True
#    unReleased.save()
#except ObjectDoesNotExist:
#    unReleased = Release()
#    unReleased.name = 'Unreleased'
#    unReleased.hidden = True
#    unReleased.isdefault = True
#    unReleased.save()

print 'done'
