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

import logging.config
import os
import datetime
import pytz

from django.db import transaction
from stratosource.models import  UserChange, SalesforceUser

__author__="mark"
__date__ ="$Oct 6, 2010 8:41:36 PM$"


SFAPIAssetMap = {
    'CustomLabels': 'label:',
    'CustomObject': 'object:',
    'CustomField': 'object:',
    'CustomSite': 'site:',
    'CustomTab': 'tab:',
    'ApexPage': '.page',
    'ApexClass': '.cls',
    'ApexTrigger': '.trigger',
    'Workflow': 'workflow:'

}

logger = logging.getLogger('console')



def perform_checkin(repodir, zipfile, branch):

    CMDLOG = repodir + '/../checkin.log'

    os.chdir(repodir)

    logger.info("Starting checkin")
    logger.info("repodir " + repodir)
    logger.info("zipfile " + zipfile)
    logger.info("branch " + branch.name)

    logger.debug('checkout')
    os.system('git reset --hard ' + branch.name + ' >>' + CMDLOG)

#    logger.debug('checking deletes')
#    logger.info("Getting list of deleted files")
#    os.system('git reset --hard %s >> %s' % (branch.name, CMDLOG))
#    os.system('rm -rf %s/*' % repodir)

    os.system('unzip -o -qq %s >> %s' % (zipfile, CMDLOG))

#    p = Popen(['git','status'], stdin=PIPE, stdout=PIPE)
#    (r, w) = (p.stdin, p.stdout)
#    rm_list = []
#    for line in r:
#        line = line.rstrip()
#        if 'deleted:' in line:
#            ix = string.find(line, 'deleted:') + 10
#            path = line[ix:].strip()
#            rm_list.append(path)
#    r.close()
#    w.close()
#    log.info("found %d file(s) to remove" % len(rm_list))

#    log.info("Resetting repo back to HEAD")
#    os.system('git reset --hard %s >> %s' % (branch.name,CMDLOG))
#    os.system('unzip -o -qq %s >> %s' % (zipfile,CMDLOG))

#    for name in rm_list:
#        os.system('git rm "%s"' % name)
#        log.info("Deleted " + name)

#    logger.info("Laying down changes")

    os.system('git add * >> %s' % CMDLOG)
    os.system('git commit -m "incremental snapshot for %s on `date`" >> %s' % (branch.name, CMDLOG))


    logger.info("Completed checkin")

##### DEFUNCT #####
"""
@transaction.atomic
def save_userchanges(branch, classes, triggers, pages):
    allchanges = classes + triggers + pages
    batch_time = datetime.datetime.now()
    userdict = dict([(user.user_id, user) for user in SalesforceUser.objects.all()])

    for change in allchanges:
        lastModId = change['LastModifiedById']
        if userdict.has_key(lastModId):
            theUser = userdict[lastModId]
        else:
            theUser = SalesforceUser()
            theUser.user_id = lastModId
            theUser.name = change['LastModifiedBy']['Name']
            theUser.email = change['LastModifiedBy']['Email']
            theUser.save()

        recents = list(UserChange.objects.filter(apex_id__exact=change['Id'], branch=branch).order_by('last_update').reverse()[:1])
        if len(recents) == 0:
            recent = UserChange()
            recent.branch = branch
            recent.apex_id = change['Id']
            recent.apex_name = change['Name']
            recent.sfuser = theUser
            lu = change['LastModifiedDate'][0:-9]
            recent.last_update = datetime.datetime.strptime(lu, '%Y-%m-%dT%H:%M:%S')
            recent.batch_time = batch_time
        else:
            recent = recents[0]


        if recent.sfuser == None or recent.sfuser.user_id != change['LastModifiedById']:
            lu = change['LastModifiedDate'][0:-9]
            recent.last_update = datetime.datetime.strptime(lu, '%Y-%m-%dT%H:%M:%S')
            recent.batch_time = batch_time
            recent.save()
    return batch_time
 """

@transaction.atomic
def save_objectchanges(branch, batch_time, chgmap, fetchtype):
    logger.info('Saving object change audit trail')
    userdict = dict([(user.name, user) for user in SalesforceUser.objects.all()])

    inserted = 0
    for aType in chgmap.keys():
        logger.debug('Type: %s' % aType)
        if fetchtype == 'code':
            if not aType in ['ApexClass','ApexTrigger','ApexPage','ApexComponent']:
                continue
        elif fetchtype == 'config':
            if aType in ['ApexClass','ApexTrigger','ApexPage','ApexComponent']:
                continue

        thirtyDays = datetime.timedelta(days = 30)
        thirtyDaysAgo = datetime.datetime.now() - thirtyDays
        logger.debug('time window=' + thirtyDaysAgo.isoformat())
        for change in chgmap[aType]:
            #chdate_tz = change.lastModifiedDate.replace(tzinfo=pytz.utc)
            chdate_tz = change.lastModifiedDate.replace(tzinfo=None)
            if chdate_tz < thirtyDaysAgo:
                # not interested in old changes, just slows down the process
                continue

            if userdict.has_key(change.lastModifiedByName):
                theUser = userdict[change.lastModifiedByName]
                #logger.debug(change)
                lastactive = theUser.lastActive  #.replace(tzinfo=pytz.utc)
                if theUser.lastActive == None or lastactive < chdate_tz:
                    theUser.lastActive = chdate_tz
                    theUser.save()
            else:
                theUser = SalesforceUser()
                theUser.userid = change.lastModifiedById[0:15]
                theUser.name = change.lastModifiedByName
                theUser.lastActive = chdate_tz
                theUser.save()
                userdict[theUser.name] = theUser
                logger.debug('new salesforce user: ' + theUser.name)

            fullName = change.fullName
            if SFAPIAssetMap.has_key(aType):
                fix = SFAPIAssetMap[aType]
                if fix.endswith(':'):
                    fullName = fix + fullName
                else:
                    fullName += fix

            lastchangelist = list(UserChange.objects.filter(branch=branch, apex_name=fullName).order_by('-last_update'))
            if len(lastchangelist) > 0:
                recent = lastchangelist[0]
            else:
                recent = UserChange()
                recent.branch = branch
                recent.apex_id = change.id
                recent.sfuser = theUser
                recent.apex_name = fullName
                recent.last_update = chdate_tz
                recent.batch_time = batch_time
                recent.object_type = aType
                recent.save()
                inserted += 1
                logger.debug('Not found, inserting %s' % fullName)

            #logger.debug('file=%s, previous change=%s, current change=%s' % (fullName, recent.last_update.isoformat(), change.lastModifiedDate.isoformat()))
            if recent.last_update is None or recent.last_update < chdate_tz:
                logger.debug('changed: userid=%s  last_update=%s lastModified=%s' % (theUser.userid, recent.last_update, chdate_tz))
                recent = UserChange()
                recent.branch = branch
                recent.apex_id = change.id
                recent.sfuser = theUser
                recent.apex_name = fullName
                recent.last_update = chdate_tz
                recent.batch_time = batch_time
                recent.object_type = aType
                recent.save()
                inserted += 1
                logger.debug('Changed, updating %s' % fullName)

    logger.info('Audited objects inserted: %d' % inserted)


