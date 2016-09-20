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
from stratosource.models import Story, Branch, DeployableObject, Release
from stratosource.management import Deployment


__author__="masmith"
__date__ ="$Sep 22, 2010 2:11:52 PM$"


class Command(BaseCommand):
    args = ''


    help = 'deploy assets to Salesforce'


    def add_arguments(self, parser):
        parser.add_argument('from', help='source branch name')
        parser.add_argument('to', help='dest branch name')
        parser.add_argument('release', help='release id')

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
        release = Release.objects.get(id=options['release'])
        from_branch = Branch.objects.get(name=options['from'])
        to_branch = Branch.objects.get(name=options['to'])

        manifest = []
        for story in release.stories.all():
            deployables = DeployableObject.objects.filter(pending_stories=story, branch=from_branch)
            dep_objects = DeployableObject.objects.filter(released_stories=story, branch=from_branch)
            deployables.select_related()
            dep_objects.select_related()
            manifest += list(deployables)
            manifest += list(dep_objects)

        manifest.sort(key=lambda object: object.type + object.filename)
        self.deploy_stories(release.stories.all(), from_branch, to_branch)


