#    Copyright 2010, 2011 Red Hat Inc.
#
#    This file is part of StratoSource.
#
#    StratoSource is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    StratoSource is distributed in the hope that it will be useful.
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with StratoSource.  If not, see <http://www.gnu.org/licenses/>.
#    
import logging
import logging.config
from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ObjectDoesNotExist
from stratosource.admin.models import Story, Branch, DeployableObject
from stratosource.admin.management import Utils
from stratosource.admin.management import Deployment
import subprocess
import os
from zipfile import ZipFile
from lxml import etree
import stratosource.admin.management.CSBase # used to initialize logging


__author__="masmith"
__date__ ="$Sep 22, 2010 2:11:52 PM$"


class Command(BaseCommand):

#    def deploy(self, objectList, from_branch, to_branch):
#        for object in objectList:
#            print object.status, object.filename, object.type, object.el_name, object.el_subtype
#        output_name = generatePackage(objectList, from_branch, to_branch)
#        agent = Utils.getAgentForBranch(to_branch, logger=logging.getLogger('deploy'));
#        return agent.deploy(output_name)

    def deploy_stories(self, stories, from_branch, to_branch):
        # get all release objects associated with the stories
        logger = logging.getLogger('deploy')
        rolist = DeployableObject.objects.filter(pending_stories__in=stories)
        deployResult = Deployment.deploy(set(rolist), from_branch, to_branch,  testOnly = False,  retain_package = True)
        if deployResult is not None:
            if not deployResult.success:
                for dm in deployResult.messages:
                    if not dm.success:
                        logger.info('fail: {0} - {1}'.format(dm.fullName, dm.problem))
                    else:
                        logger.info('pass: {0}'.format(dm.fullName))
                raise CommandError('deployment failed')


    def handle(self, *args, **options):
        if len(args) < 6: raise CommandError('usage: deploy <source repo> <source branch> <dest repo> <dest branch> story <storyid>')

        if args[4] == 'story':
            stories = [Story.objects.get(rally_id = storyid) for storyid in args[5:]]
#            story = Story.objects.get(rally_id=args[5])
            if not story: raise CommandException("invalid story")
            from_branch = Branch.objects.get(repo__name__exact=args[0], name__exact=args[1])
            if not from_branch: raise CommandException("invalid source branch")
            to_branch = Branch.objects.get(repo__name__exact=args[2], name__exact=args[3])
            if not to_branch: raise CommandException("invalid destination branch")
            #self.deploy_stories([story], from_branch, to_branch)
            self.deploy_stories(stories, from_branch, to_branch)


