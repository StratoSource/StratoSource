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
from stratosource.management import CSBase
import os
import logging
from stratosource.management.SalesforceAgent import SalesforceAgent
from stratosource.management import ConfigCache


__author__="mark"
__date__ ="$Sep 14, 2010 9:09:55 PM$"

def getAgentForBranch(branch, logger = None):
    if not logger: logger = logging.getLogger('root')

    user = branch.api_user
    password = branch.api_pass
    authkey = branch.api_auth
    if authkey is None: authkey = ''
    svcurl = 'https://' + branch.api_env + '.salesforce.com/services/Soap/u/' + CSBase.CS_SF_API_VERSION #branch.api_ver

#    print("user='%s' path='%s' types=[%s] url='%s'", user, path, ' '.join(types), svcurl)

    partner_wsdl = 'file://' + os.path.join(CSBase.CSCONF_DIR, 'partner.wsdl')
    meta_wsdl = 'file://' + os.path.join(CSBase.CSCONF_DIR, 'metadata.wsdl')

    proxy_host = ConfigCache.get_config_value('proxy.host')
    proxy_port = ConfigCache.get_config_value('proxy.port')

    if len(proxy_host) > 0 and len(proxy_port) > 0:
        agent = SalesforceAgent(partner_wsdl, meta_wsdl, clientLogger=logger, proxy_host=proxy_host, proxy_port=proxy_port)
    else:
        agent = SalesforceAgent(partner_wsdl, meta_wsdl, clientLogger=logger)

    agent.login(user, password+authkey,server_url=svcurl)
    return agent

def doGrep(codedir, ext, text):
    import os, subprocess
    os.chdir(codedir)
    cmd = "grep -in '{0}' *.{1}".format(text, ext)
    ps = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    output = ps.communicate()[0]
    lines = output.split('\n')
    results = []
    for line in lines:
        parts = line.split(':')
        if len(parts) >= 3:
            filename = parts[0]
            linenum = parts[1]
            text = ':'.join(parts[2:])

            results.append({'filename': filename, 'match': text.strip(), 'linenum': linenum})
    return results
