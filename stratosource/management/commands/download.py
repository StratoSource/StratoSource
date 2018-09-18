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
import logging
import os

from django.utils import timezone

from stratosource.models import Branch
from stratosource.management import Utils

__author__="mark"
__date__ ="$Sep 7, 2010 9:02:55 PM$"

logger = logging.getLogger('console')


class Command(BaseCommand):
    args = ''
    help = 'download assets from Salesforce'

    def add_arguments(self, parser):
        parser.add_argument('repo', help='repository name')
        parser.add_argument('branch', help='branch name')
        parser.add_argument('type', help='type of download (config or code)')

    def handle(self, *args, **options):

        br = Branch.objects.get(repo__name__exact=options['repo'], name__exact=options['branch'])
        if not br: raise CommandError("invalid repo/branch")

        downloadOnly = False
#        if len(args) > 2 and args[2] == '--download-only': downloadOnly = True

        agent = Utils.getAgentForBranch(br, logger=logger)

        path = br.api_store
        if options['type'] == 'code':
            types = ['ApexClass','ApexTrigger','ApexPage','ApexComponent']
        elif options['type'] == 'config':
            types = [aType.strip() for aType in br.api_assets.split(',')]

        filename = os.path.join(path, '{0}_fetch_{1}_{2}.zip'.format(options['type'], br.repo.name, br.name))

        logger.info('fetching audit data')
        chgmap = agent.retrieve_changesaudit(types)

        logger.info('retrieving %s from %s:%s for %s' % (options['type'], br.repo.name, br.name, ','.join(types)))
        agent.retrieve_meta(types, filename)
        agent.close()
        logger.info('finished download')

        if not downloadOnly:
            from stratosource.management.checkin import perform_checkin, save_objectchanges
            perform_checkin(os.path.join(br.repo.location, br.name), filename, br)
            batch_time = timezone.now()
            logger.debug('saving audit...')
            save_objectchanges(br, batch_time, chgmap, options['type'])
            #os.remove(filename)

