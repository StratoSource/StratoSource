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
from django.db import transaction

from stratosource.management import SalesforceAgent
from stratosource.management.CSBase import COMMENT_MARKER
from stratosource.models import UserChange, SalesforceUser

__author__ = "mark"
__date__ = "$Oct 6, 2010 8:41:36 PM$"


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

    cmdlog = repodir + '/../checkin.log'

    os.chdir(repodir)

    logger.info("Starting checkin")
    logger.info("repodir " + repodir)
    logger.info("zipfile " + zipfile)
    logger.info("branch " + branch.name)

    logger.debug('checkout')
    os.system(f'git reset --hard {branch.name} >> {cmdlog}')
    os.system(f'unzip -o -qq {zipfile} >> {cmdlog}')
    os.system(f'git add * >> {cmdlog}')
    os.system(f'git commit -m "{COMMENT_MARKER} incremental snapshot for {branch.name} on `date`" >> {cmdlog}')
    logger.info("Completed checkin")


@transaction.atomic
def save_objectchanges(branch, batch_time, chgmap, fetchtype):
    logger.info('Saving object change audit trail')
    userdict = dict([(user.name, user) for user in SalesforceUser.objects.all()])

    inserted = 0
    for aType in chgmap.keys():
        logger.debug('Type: %s' % aType)
        if fetchtype == 'code':
            if aType not in SalesforceAgent.CODE_TYPES:
                continue
        elif fetchtype == 'config':
            if aType in SalesforceAgent.CODE_TYPES:
                continue

        thirty_days = datetime.timedelta(days = 30)
        thirty_days_ago = datetime.datetime.now() - thirty_days
        logger.debug('time window=' + thirty_days_ago.isoformat())
        for change in chgmap[aType]:
            #chdate_tz = change.lastModifiedDate.replace(tzinfo=pytz.utc)
            chdate_tz = change.lastModifiedDate.replace(tzinfo=None)
            if chdate_tz < thirty_days_ago:
                # not interested in old changes, just slows down the process
                continue

            if change.lastModifiedByName in userdict:
                the_user = userdict[change.lastModifiedByName]
                #logger.debug(change)
                lastactive = the_user.lastActive  # .replace(tzinfo=pytz.utc)
                if the_user.lastActive is None or lastactive < chdate_tz:
                    the_user.lastActive = chdate_tz
                    the_user.save()
            else:
                the_user = SalesforceUser()
                the_user.userid = change.lastModifiedById[0:15]
                the_user.name = change.lastModifiedByName
                the_user.lastActive = chdate_tz
                the_user.save()
                userdict[the_user.name] = the_user
                logger.debug('new salesforce user: ' + the_user.name)

            fullName = change.fullName
            if aType in SFAPIAssetMap:
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
                recent.sfuser = the_user
                recent.apex_name = fullName
                recent.last_update = chdate_tz
                recent.batch_time = batch_time
                recent.object_type = aType
                recent.save()
                inserted += 1
#                logger.debug('Not found, inserting %s' % fullName)

            #logger.debug('file=%s, previous change=%s, current change=%s' % (fullName, recent.last_update.isoformat(), change.lastModifiedDate.isoformat()))
            if recent.last_update is None or recent.last_update < chdate_tz:
#                logger.debug('changed: userid=%s  last_update=%s lastModified=%s' % (the_user.userid, recent.last_update, chdate_tz))
                recent = UserChange()
                recent.branch = branch
                recent.apex_id = change.id
                recent.sfuser = the_user
                recent.apex_name = fullName
                recent.last_update = chdate_tz
                recent.batch_time = batch_time
                recent.object_type = aType
                recent.save()
                inserted += 1
#                logger.debug('Changed, updating %s' % fullName)

    logger.info('Audited objects inserted: %d' % inserted)


