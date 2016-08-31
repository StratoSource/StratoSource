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
#!/usr/bin/env python
# myfilters.py
# Some custom filters for dictionary lookup.
from django.template.defaultfilters import register

@register.filter(name='lookup')
def lookup(dict, index):
    if index in dict:
        return dict[index]
    return index

@register.filter(name='runtime')
def runtime(secs):
    hours = secs / 3600
    secs = secs - (hours * 3600)
    mins = secs / 60
    secs = secs - (mins * 60)
    return '{0}h {1}m {2}s'.format(hours, mins, secs)

