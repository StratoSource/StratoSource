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
import threading

from urlparse import urlparse

from suds.client import Client
import suds
import binascii
import time
import logging
import os
import httplib, urllib
import json
#from mq import MQClient
from stratosource.models import EmailTemplateFolder

__author__="mark"
__date__ ="$Aug 15, 2010 9:48:38 PM$"

_API_VERSION = 37.0
_DEFAULT_LOGNAME = '/var/sftmp/agent.log'
_METADATA_TIMEOUT=60 * 80
_METADATA_POLL_SLEEP=10
_DEPLOY_TIMEOUT=6 * 10 * 60   # 1 hour
_DEPLOY_POLL_SLEEP=10

class LoginError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)

class Bag:
    def __str__(self):
        return repr(self.__dict__)

#
# Rxperiement with multithreading and suds, but making it easy to revert with just this boolean
# because it may cause problems.
#
multithreaded = True

class EmailFolderThread (threading.Thread):

    def __init__(self, folder, meta):
        threading.Thread.__init__(self)
        self.folder = folder
        self.meta = meta
        self.email_paths = []
        self.done = False
        self.started = False

    def run(self):
        self.started = True
        query = self.meta.factory.create('ListMetadataQuery')
        query.type = 'EmailTemplate'
        query.folder = self.folder
        props = self.meta.service.listMetadata([query], _API_VERSION)
        for prop in props:
            self.email_paths.append(prop.fullName)
        self.done = True




class SalesforceAgent:

    def __init__(self, partner_wsdl_url, metadata_wsdl_url = None, clientLogger = None, proxy_host=None, proxy_port=None):
        if clientLogger is None:
#            logging.basicConfig(level=logging.DEBUG)
#            self.logname = _DEFAULT_LOGNAME
            self.logger = logging.getLogger(__file__)
        else:
            self.logger = clientLogger
        self.login_result = None

        proxyDict = dict()
        if not proxy_host is None and not proxy_port is None and len(proxy_host) > 0 and len(proxy_port) > 0:
            proxyDict['http'] = 'http://%s:%s' % (proxy_host, proxy_port)
            proxyDict['https'] = 'https://%s:%s' % (proxy_host, proxy_port)
            os.environ['http_proxy'] = proxyDict['https']
            os.environ['https_proxy'] = proxyDict['https']

        if metadata_wsdl_url:
            self.meta = Client(metadata_wsdl_url, proxy=proxyDict)
        else:
            self.meta = None
        self.partner = Client(partner_wsdl_url, proxy=proxyDict)
        self.proxy_host = proxy_host
        self.proxy_port = proxy_port

    def set_logname(self, name):
        self.logname = name
        logging.basicConfig(filename=name,level=logging.DEBUG)
        self.logger = logging.getLogger(__file__)

    def getSessionId(self):
        return self.sid.sessionId
        
    def getServerLocation(self):
        return urlparse(self.login_result.serverUrl).netloc

    def login(self, user, password, server_url = None):
        if server_url: self.partner.set_options(location=server_url)
        try:
            self.login_result = self.partner.service.login(user, password)
        except suds.WebFault as sf:
#            MQClient().publish(str(sf), level='error').close()
            raise LoginError(str(sf))
        self.sid = self.partner.factory.create('SessionHeader')
        self.sid.sessionId = self.login_result.sessionId
        self.partner.set_options(soapheaders=self.sid)
        self.partner.set_options(location=self.login_result.serverUrl)

        self.meta.set_options(soapheaders=self.sid)
        self.meta.set_options(location=self.login_result.metadataServerUrl)
        self.serverloc = urlparse(self.login_result.serverUrl).netloc

    def close(self):
        if not self.login_result:
            raise Exception('Initialization error: not logged in')
    #
    # try to avoid timeouts by not logging out, which invalidates shared session of other
    # jobs using the same salesforce api credentials.
    #
#        self.partner.service.logout()
        self.login_result = None

    def getSalesforceEmailTemplateFolders(self):
        rest_conn = self.setupForRest()
        params = urllib.urlencode({'q': "select Id, Name, DeveloperName from Folder where Type = 'Email'"})
        data = self._invokeGetREST(rest_conn, "query/?%s" % params)

        if not data == None:
            records = data['records']
            folders = [record['DeveloperName'] for record in records]
        else:
            folders = []
        return folders

    def _buildEmailTemplatesPackage(self):
        folder_rows = EmailTemplateFolder.objects.all()
        folders = [row.name for row in folder_rows];

        emailpaths = []
        if multithreaded:
            #
            # kept 4 threads running at all times to retrieve folder content
            #
            threads = [EmailFolderThread(folder, self.meta) for folder in folders]
            available_slots = 4
            while True:
                for i in range(0, len(threads)):
                    if threads[i].started and threads[i].done:
                        available_slots += 1
                        threads[i].started = False
                    if not threads[i].started and not threads[i].done and available_slots > 0:
                        self.logger.debug('listing contents of email folder %s' % threads[i].folder)
                        threads[i].started = True
                        threads[i].start()
                        available_slots -= 1
                time.sleep(1)
                if available_slots >= 4:
                    break

            # collect up the results of each thread
            for i in range(0,len(threads)):
                if not threads[i].done:
                    print('oops! a thread is still running')
                emailpaths.extend(threads[i].email_paths)
        else:
            #
            # single threading version
            #
            query = self.meta.factory.create('ListMetadataQuery')
            query.type = 'EmailTemplate'
            emailpaths = []
            print('folders = %s' % (len(folders),))
            for folder in folders:
                query.folder = folder
                self.logger.debug('listing contents of email folder %s' % folder)
                props = self.meta.service.listMetadata([query], _API_VERSION)
                for prop in props:
                    emailpaths.append(prop.fullName)

        ptm = self.meta.factory.create('PackageTypeMembers')
        ptm.name = 'EmailTemplate'
        ptm.members = [emailpath for emailpath in emailpaths]
        return ptm

    def _buildCustomObjectsPackage(self):
        self.logger.info('loading Salesforce catalog for custom field discovery')
        query = self.meta.factory.create('ListMetadataQuery')
        query.type = 'CustomObject'
        props = self.meta.service.listMetadata([query], _API_VERSION)
        self.logger.info('catalog contains %d objects' % len(props))
        ptm = self.meta.factory.create('PackageTypeMembers')
        ptm.name = 'CustomObject'
        ptm.members = [prop.fullName for prop in props]
        return ptm

    def _buildMetaPackage(self, querytype):
        self.logger.info('loading ' + querytype)
        query = self.meta.factory.create('ListMetadataQuery')
        query.type = querytype
        props = self.meta.service.listMetadata([query], _API_VERSION)
        self.logger.info('%s contains %d objects' % (querytype, len(props)))
        ptm = self.meta.factory.create('PackageTypeMembers')
        ptm.name = querytype
        ptm.members = [prop.fullName for prop in props]
        return ptm

    def retrieve_objectchanges(self):
        query = self.meta.factory.create('ListMetadataQuery')
        query.type = 'CustomObject'
        props = self.meta.service.listMetadata([query], _API_VERSION)
        return props

    def retrieve_changesaudit(self, types):
        supportedtypelist = ['ApexClass','ApexPage','ApexTrigger','ApexComponent','Workflow','ApprovalProcess']

        # get intersection of requested types and those we support
        typelist = list(set(supportedtypelist) & set(types))
        self.logger.info('loading changes for %s' % ','.join(typelist))
        for atype in typelist:
            if atype == 'CustomObject': typelist.append('CustomField')
        results = {}
        query = self.meta.factory.create('ListMetadataQuery')
        for aType in typelist:
            query.type = aType
            results[aType] = self.meta.service.listMetadata([query], _API_VERSION)
            self.logger.debug('Loaded %d records for type %s' % (len(results[aType]), aType))

        #
        # now do the types that diverge from the norm
        #

    #        rest_conn = self.setupForRest(pod)
    #        self.logger.info('loading changes for EmailTemplate')
    #        tmpemails = self._getEmailChangesMap(rest_conn)
    #        etemplates = []
    #        for tmpemail in tmpemails:
    #            template = Bag()
    #            template.__dict__['fullName'] = tmpemail['DeveloperName'] + '.email'
    #            template.__dict__['lastModifiedById'] = tmpemail['LastModifiedById']
    #            template.__dict__['lastModifiedByName'] = tmpemail['LastModifiedBy']['Name']
    #            template.__dict__['id'] = tmpemail['Id']
    #            lmd = tmpemail['LastModifiedDate'][0:-9]
    #            template.__dict__['lastModifiedDate'] = datetime.datetime.strptime(lmd, '%Y-%m-%dT%H:%M:%S')
    #            etemplates.append(template)
    #        results['EmailTemplate'] = etemplates
    #        self.logger.debug('Loaded %d EmailTemplate records' % len(etemplates))
        return results

    def setupForRest(self):
        self.rest_headers = {"Authorization": "OAuth %s" % self.getSessionId(), "Content-Type": "application/json" }
        self.logger.info('connecting to REST endpoint at %s' % serverloc)
        httpcon = httplib.HTTPSConnection(self.serverloc)
        if not self.proxy_host is None: httpcon.set_tunnel(self.proxy_host, self.proxy_port)
        return httpcon

    def _getChangesMap(self, rest_conn, sfobject, withstatus=True):
        if withstatus:
            params = urllib.urlencode({'q': "select Id, Name, LastModifiedById, LastModifiedBy.Name, LastModifiedBy.Email, LastModifiedDate from %s where Status = 'Active' and NamespacePrefix = '' order by name" % sfobject})
        else:
            params = urllib.urlencode({'q': "select Id, Name, LastModifiedById, LastModifiedBy.Name, LastModifiedBy.Email, LastModifiedDate from %s where NamespacePrefix = '' order by name" % sfobject})
        data = self._invokeGetREST(rest_conn, "query/?%s" % params)
        if not data == None:
            return data['records']
        return None

    def _getEmailChangesMap(self, rest_conn):
        params = urllib.urlencode({'q': "select Id, Name, DeveloperName, LastModifiedById, LastModifiedBy.Name, LastModifiedBy.Email, LastModifiedDate from EmailTemplate where NamespacePrefix = '' order by name"})
        data = self._invokeGetREST(rest_conn, "query/?%s" % params)
        if not data == None:
            return data['records']
        return None

    def _invokePostREST(self, rest_conn, url, payload):
        rest_conn.request("POST", '/services/data/v%s/%s' % (_API_VERSION, url), payload, headers=self.rest_headers)
        response = rest_conn.getresponse()
        resultPayload = response.read()
        if response.status != 201:
            print(response.status, response.reason)
            return None
        data = json.loads(resultPayload)
        return data

    def _invokeGetREST(self,rest_conn,  url):
        self.logger.debug('invoking /services/data/v%s/%s' % (_API_VERSION, url))
        rest_conn.request("GET", '/services/data/v%s/%s' % (_API_VERSION, url), headers=self.rest_headers)
        response = rest_conn.getresponse()
        resultPayload = response.read()
        if response.status != 200:
            print(response.status, response.reason)
            print(resultPayload)
            return None
        data = json.loads(resultPayload)
        recs = data['records']
        while data.has_key('nextRecordsUrl'):
            nextRecordsUrl = data['nextRecordsUrl']
            if nextRecordsUrl:
                rest_conn.request('GET', nextRecordsUrl, headers=self.rest_headers)
                response = rest_conn.getresponse()
                resultPayload = response.read()
                data = json.loads(resultPayload)
                recs.extend(data['records'])
            else:
              break
        data['records'] = recs
        return data

    def retrieve_meta(self, types, outputname='/var/sftmp/retrieve.zip'):
        if not self.login_result:
            raise Exception('Initialization error: not logged in')
        if not self.meta:
            raise Exception('metadata API not initialized')
        request = self.meta.factory.create('RetrieveRequest')
        request.apiVersion = _API_VERSION
        pkg = self.meta.factory.create('Package')
        pkg.fullName = ['*']
        pkg.version = _API_VERSION
        pkg.apiAccessLevel = 'Unrestricted'
        pkgtypes = []
        print("fetching types {}".format(types))
        for type in types:
            if type == 'CustomObject':
                pkgtypes.append(self._buildCustomObjectsPackage())
            elif type == 'EmailTemplate':
                pkgtypes.append(self._buildEmailTemplatesPackage())
            elif type == 'GlobalPicklist':
                pkgtypes.append(self._buildMetaPackage('GlobalPicklist'))
            else:
                pkgtype = self.meta.factory.create('PackageTypeMembers')
                pkgtype.members = ['*']
                pkgtype.name = type
                pkgtypes.append(pkgtype)
        pkg.types = pkgtypes
        request.unpackaged = [pkg]
        request.singlePackage = False

        countdown = _METADATA_TIMEOUT
        asyncResult = self.meta.service.retrieve(request)
        asyncResultId = asyncResult.id
        while True:
            self.logger.info('polling.. %s' % str(countdown))
            time.sleep(_METADATA_POLL_SLEEP)
            countdown -= _METADATA_POLL_SLEEP
            if countdown <= 0: break
            retrieveResult = self.meta.service.checkRetrieveStatus([asyncResultId], False)[0]
            if retrieveResult: break

        #if retrieveResult.state != 'Completed':
        #    self.logger.error('Retrieving package: ' + retrieveResult.message)
        #    MQClient().publish('Metadata retrieval did not complete: %s' % (asyncResult.message,), level='error').close()
        #    raise Exception(asyncResult.message)

        result = self.meta.service.checkRetrieveStatus([asyncResultId], True)

    #    if result.messages != None and len(result.messages) > 0:
    #        print 'Error: ' + '\n'.join([r.problem for r in result.messages])
    #        raise Exception('Retrieval error: ' + result.messages[0].problem)

        zip = binascii.a2b_base64(result.zipFile)
        out = open(outputname, 'w')
        out.write(zip)
        out.close()

    def deploy(self, zipfilename,  checkOnly = False):
        zipfile = open(zipfilename, 'rb')
        zip = zipfile.read()
        zipfile.close()
        zip64 = binascii.b2a_base64(zip)
        deploy_options = self.meta.factory.create('DeployOptions')
        deploy_options.allowMissingFiles = 'false'
        deploy_options.autoUpdatePackage = 'true'
        deploy_options.checkOnly = 'true' if checkOnly else 'false'
        deploy_options.ignoreWarnings = 'false'
        deploy_options.performRetrieve = 'false'
        deploy_options.purgeOnDelete = 'false'
        deploy_options.rollbackOnError = 'true'
        deploy_options.runAllTests = 'false'
        deploy_options.singlePackage = 'true'

        result = self.meta.service.deploy(zip64, deploy_options)
        countdown = _DEPLOY_TIMEOUT
        while not result.done:
            self.logger.info('polling..%s' % str(countdown))
            time.sleep(_DEPLOY_POLL_SLEEP)
            countdown -= _DEPLOY_POLL_SLEEP
            if countdown <= 0: raise Exception('Deployment timed out')
            result = self.meta.service.checkRetrieveStatus([result.id])[0]
            print(result)
            print("Status is: %s" % result.state)
        if result.state != 'Completed':
            raise Exception(result.message)
        deployResult = self.meta.service.checkDeployStatus(result.id)
        return deployResult


if __name__ == "__main__":
    print "Hello World"
