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
from django.core.exceptions import ObjectDoesNotExist

from stratosource.management.CSBase import COMMENT_MARKER
from stratosource.models import Branch, Commit
import subprocess
import logging
from datetime import datetime
import os

__author__ = "masmith"
__date__ = "$Sep 22, 2010 2:11:52 PM$"

logger = logging.getLogger('console')


class Command(BaseCommand):

    def parse_commits(self, branch, start_date):
        cwd = os.getcwd()
        try:
            os.chdir(os.path.join(branch.repo.location, branch.name))
            subprocess.check_call(["git", "checkout", branch.name])
            subprocess.check_call(["git", "reset", "--hard", "{0}".format(branch.name)])
            p = subprocess.Popen(['git', 'log'], stdout=subprocess.PIPE)
            commits = []
            hash = ""
            author = ""
            commitdate = ""
            comment = ""
            for line in p.stdout:
                line = line.decode('utf-8')
                line = line.rstrip()
                if line.startswith("commit "):
                    if len(hash) > 0:
                        if commitdate >= start_date:
                            map = {'hash': hash, 'author': author, 'date': commitdate, 'comment': comment}
                            commits.append(map)
                            if len(map) >= 10: break  # no need to do more than 10 really
                        hash = ""
                        author = ""
                        commitdate = ""
                        comment = ""
                    hash = line[7:]
                elif line.startswith("Author: "):
                    author = line[8:]
                elif line.startswith("Date:  "):
                    # logger.debug('parsing date from ' + line[8:-6])
                    commitdate = datetime.strptime(line[8:-6], '%a %b %d %H:%M:%S %Y')
                elif len(line) > 4:
                    comment += line.strip()
            if len(hash) > 0 and COMMENT_MARKER in comment:
                map = {'hash': hash, 'author': author, 'date': commitdate, 'comment': comment}
                commits.append(map)
            p.stdout.close()
            logger.info('commits = ' + str(len(commits)))
            return commits
        finally:
            os.chdir(cwd)

    def add_arguments(self, parser):
        parser.add_argument('repo', help='repository name')
        parser.add_argument('branch', help='branch name')

    def handle(self, *args, **options):

        br = Branch.objects.get(repo__name__exact=options['repo'], name__exact=options['branch'])
        if not br: raise CommandError("invalid repo/branch")

        # start_date = datetime(2000, 1, 1, 0, 0, tzinfo=here_tz)
        start_date = datetime(2000, 1, 1, 0, 0)

        commits = self.parse_commits(br, start_date)
        commits.reverse()  # !! must be in reverse chronological order from oldest to newest
        prev_commit = None
        for acommit in commits:
            #           logger.debug('processing commit ' + acommit['hash'])
            try:
                existing = Commit.objects.get(hash__exact=acommit['hash'])
                if existing:
                    prev_commit = acommit
                    #                    logger.debug('hash exists')
                    continue
            except ObjectDoesNotExist:
                logger.debug('new hash')
                pass

            logger.info('adding commit %s for branch %s' % (acommit['hash'], br.name))
            if prev_commit: logger.info('prev hash = ' + prev_commit['hash'])
            newcommit = Commit()
            newcommit.branch = br
            newcommit.hash = acommit['hash']
            if prev_commit: newcommit.prev_hash = prev_commit['hash']
            newcommit.comment = acommit['comment']
            newcommit.date_added = acommit['date']  # datetime.strptime(acommit['date'][:-6], '%a %b %d %H:%M:%S %Y')
            newcommit.save()
            prev_commit = acommit
