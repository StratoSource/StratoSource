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
from django.core.management.base import BaseCommand, CommandError
from suds.client import Client
import os
import base64
import sys
import httplib, urllib
import json
import time
import datetime
from stratosource.admin.management import CSBase
from stratosource.admin.management import Utils
from stratosource.admin.models import Branch, Repo, UnitTestBatch, UnitTestRun, UnitTestRunResult
from stratosource.admin.management import UnitTestRunUtil


__author__="masmith"
__date__ ="$Nov 1, 2011 10:41:44 AM$"



class Command(BaseCommand):

    def handle(self, *args, **options):

        if len(args) < 2: raise CommandError('usage: runtests <repo alias> <branch>')
        repo = Repo.objects.get(name__exact=args[0])
        self.branch = Branch.objects.get(repo=repo, name__exact=args[1])

        self.agent = Utils.getAgentForBranch(self.branch)
        self.rest_headers = {"Authorization": "OAuth %s" % self.agent.getSessionId(), "Content-Type": "application/json" }
        serverloc = self.branch.api_pod + '.salesforce.com'
        self.rest_conn = httplib.HTTPSConnection(serverloc)
        self.startTests()
        self.monitorTests()
        self.rest_conn.close()


    def startTests(self):
        self.classList = self.getClassList()

        utb = UnitTestBatch()
        utb.batch_time = datetime.datetime.now()
        utb.branch = self.branch
        utb.save()
        
        self.utb = utb

        count = 0
        self.testItemIdList = {}
        for cls in self.classList:
            body = cls['Body'].lower()
            if body.find('testmethod') > 0:
                #if count == 20: break
                count += 1
                print '%s -> %s' % (cls['Id'], cls['Name'])
                data = self.invokePostREST("sobjects/ApexTestQueueItem", json.dumps({'ApexClassId':cls['Id']}))
                if data != None and data['success'] == True:
                    self.testItemIdList[data['id']] = None
                print 'data: %s' % data
        print '** tests scheduled'


    def invokePostREST(self, url, payload):
        self.rest_conn.request("POST", '/services/data/v%s/%s' % (CSBase.CS_SF_API_VERSION, url), payload, headers=self.rest_headers)
        response = self.rest_conn.getresponse()
        resultPayload = response.read()
        if response.status != 201:
            print response.status, response.reason
            return None
        data = json.loads(resultPayload)
        return data

    def invokeGetREST(self, url):
        return self._invokeGetREST('/services/data/v%s/%s' % (CSBase.CS_SF_API_VERSION, url))

    def _invokeGetREST(self, url):
        self.rest_conn.request("GET", url, headers=self.rest_headers)
        response = self.rest_conn.getresponse()
        resultPayload = response.read()
        if response.status != 200:
            print response.status, response.reason
            print resultPayload
            return None
        data = json.loads(resultPayload)
        return data

    def monitorTests(self):
        timer = 5
#        self.batch_time = datetime.datetime.now()
        self.completedTests = {}
        while timer > 0 and len(self.testItemIdList) > 0:
            print '-- %d tests remaining' % len(self.testItemIdList)
            params = urllib.urlencode({'q': "select Id, ApexClassId, SystemModstamp from ApexTestQueueItem where Status = 'Completed'"})
            data = self.invokeGetREST("query/?%s" % params)
            if not data == None:
                records = data['records']
                print 'fetched %d records' % len(records)
                while data.has_key('nextRecordsUrl'):
                    nextRecordsUrl = data['nextRecordsUrl']
                    print 'nextRecordsUrl=%s' % nextRecordsUrl
                    data = self._invokeGetREST(nextRecordsUrl)
                    if data.has_key('records'):
                        morerecords = data['records']
                        records.extend(morerecords)
                        print 'fetched %d more records' % len(morerecords)
                for record in records:
                    if not self.isPendingTest(record): continue  # make sure only looking at OUR tests
                    timer = 5
#                    print 'record:'
#                    print record
                    if not self.completedTests.has_key(record['Id']):
                        self.processCompletedQueueItem(record)
            print '%d: sleeping...' % timer
            time.sleep(60)
            timer -= 1
        UnitTestRunUtil.processRun(self.utb.id)


    def processCompletedQueueItem(self, queueItem):
        self.completedTests[queueItem['Id']] = queueItem
        del self.testItemIdList[queueItem['Id']]
        params = urllib.urlencode({'q': "select Id, ApexClassId, SystemModstamp, TestTimestamp, MethodName, Outcome, Message from ApexTestResult where QueueItemId = '%s'" % queueItem['Id']})
        data = self.invokeGetREST("query/?%s" % params)
        

        utr = UnitTestRun()
        utr.batch = self.utb
        utr.apex_class_id = queueItem['ApexClassId']
        utr.branch = self.branch
        for cls in self.classList:
            if cls['Id'] == utr.apex_class_id: utr.class_name = cls['Name']
        utr.save()
        if not data == None:
            records = data['records']
            utr.tests = len(records)
            for record in records:
                utrr = UnitTestRunResult()
                utrr.test_run = utr
                dt = record['TestTimestamp'][0:-9]
                utrr.start_time = datetime.datetime.strptime(dt, '%Y-%m-%dT%H:%M:%S')
                dt = record['SystemModstamp'][0:-9]
                utrr.end_time = datetime.datetime.strptime(dt, '%Y-%m-%dT%H:%M:%S')
                utrr.method_name = record['MethodName']
                utrr.outcome = record['Outcome']
                message = record['Message']
                if not message is None: message = message[0:254]
                utrr.message = message
                utrr.save()
                if utrr.outcome != 'Pass': utr.failures += 1
            utr.save()


    def isPendingTest(self, queue_item):
        for testid in self.testItemIdList.keys():
            if testid == queue_item['Id']: return True
        return False

    def getClassList(self):
        params = urllib.urlencode({'q': "select id, name, body from ApexClass where Status = 'Active' and NamespacePrefix = '' order by name"})
        data = self.invokeGetREST("query/?%s" % params)
        if not data == None:
            records = data['records']
            while data.has_key('nextRecordsUrl'):
                nextRecordsUrl = data['nextRecordsUrl']
#                print 'nextRecordsUrl=%s' % nextRecordsUrl
                data = self._invokeGetREST(nextRecordsUrl)
                if not data is None and data.has_key('records'):
                    nextrecords = data['records']
                    records.extend(nextrecords)
#                    print 'fetched %d more records' % len(nextrecords)
                else:
                    break
            return records
        return None

