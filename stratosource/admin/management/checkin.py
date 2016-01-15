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
import datetime
import string
from subprocess import PIPE, Popen

from django.db import transaction
from stratosource.models import Branch, UserChange, SalesforceUser

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

#    logging.basicConfig(filename=os.path.join('../checkin.log'), format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    log = logging.getLogger('checkin')
    log.setLevel(logging.DEBUG)

    logger.debug('Starting checkin...')
    log.info("Starting checkin")
    log.info("repodir " + repodir)
    log.info("zipfile " + zipfile)
    log.info("branch " + branch.name)

    logger.debug('checkout')
    os.system('git reset --hard ' + branch.name + ' >>' + CMDLOG)

    logger.debug('checking deletes')
    log.info("Getting list of deleted files")
    os.system('git reset --hard %s >> %s' % (branch.name, CMDLOG))
    os.system('rm -rf %s/*' % repodir)
    os.system('unzip -o -qq %s >> %s' % (zipfile, CMDLOG))

    p = Popen(['git','status'], stdin=PIPE, stdout=PIPE)
    (r, w) = (p.stdin, p.stdout)
    rm_list = []
    for line in r:
        line = line.rstrip()
        if 'deleted:' in line:
            ix = string.find(line, 'deleted:') + 10
            path = line[ix:].strip()
            rm_list.append(path)
    r.close()
    w.close()
    log.info("found %d file(s) to remove" % len(rm_list))

    log.info("Resetting repo back to HEAD")
    os.system('git reset --hard %s >> %s' % (branch.name,CMDLOG))
    os.system('unzip -o -qq %s >> %s' % (zipfile,CMDLOG))

    for name in rm_list:
        os.system('git rm "%s"' % name)
        log.info("Deleted " + name)

    log.info("Laying down changes")

    os.system('git add * >> %s' % CMDLOG)
    os.system('git commit -m "incremental snapshot for %s on `date`" >> %s' % (branch.name, CMDLOG))


    log.info("Completed checkin")

##### DEFUNCT #####
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
 
@transaction.atomic
def save_objectchanges(branch, batch_time, chgmap):
    logger = logging.getLogger('download')
    logger.info('Saving object change audit trail')
    userdict = dict([(user.name, user) for user in SalesforceUser.objects.all()])

    inserted = 0
    for aType in chgmap.keys():
        logger.debug('Type: %s' % aType)
        thirtyDays = datetime.timedelta(days = 30)
        thirtyDaysAgo = datetime.now() - thirtyDays
        for change in chgmap[aType]:
            if change.lastModifiedDate < thirtyDaysAgo:
                # not interested in old changes, just slows down the process
                continue

            if userdict.has_key(change.lastModifiedByName):
                theUser = userdict[change.lastModifiedByName]
                if theUser.lastActive < change.lastModifiedDate:
                    theUser.lastActive = change.lastModifiedDate
                    theUser.save()
            else:
                theUser = SalesforceUser()
                theUser.userid = change.lastModifiedById[0:15]
                theUser.name = change.lastModifiedByName
                theUser.lastActive = change.lastModifiedDate
                theUser.save()
                userdict[theUser.name] = theUser

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
                recent.last_update = change.lastModifiedDate
                recent.batch_time = batch_time
                recent.object_type = aType
                recent.save()
                inserted += 1
                logger.debug('Not found, inserting %s' % fullName)

            if recent.last_update < change.lastModifiedDate:
                logger.debug('changed: userid=%s userid=%s  last_update=%s lastModified=%s' % (recent.sfuser.userid, theUser.userid, recent.last_update, change.lastModifiedDate))
                recent = UserChange()
                recent.branch = branch
                recent.apex_id = change.id
                recent.sfuser = theUser
                recent.apex_name = fullName
                recent.last_update = change.lastModifiedDate
                recent.batch_time = batch_time
                recent.object_type = aType
                recent.save()
                inserted += 1
                logger.debug('Changed, inserting %s' % fullName)

    logger.info('Audited objects inserted: %d' % inserted)


