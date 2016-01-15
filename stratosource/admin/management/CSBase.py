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

import logging
import logging.config
import os
from ss2 import settings


##
# Location constants
##
_CSHOME=settings.BASE_DIR
CSCONF_DIR=os.path.join(_CSHOME, 'stratosource', 'conf')
CS_SF_API_VERSION = '29.0'



def loadFile(name):
   with open(name) as f:
       return f.read()


#logging.config.fileConfig(os.path.join(CSCONF_DIR, 'logging.conf'))
#logging.basicConfig(filename='/tmp/cloudsrc.log', level=logging.DEBUG)

