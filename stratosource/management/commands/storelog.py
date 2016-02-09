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
from stratosource.models import Branch, BranchLog

import fileinput


__author__="jkruger"
__date__ ="$Oct 13, 2011 9:19 AM$"

class Command(BaseCommand):


    def add_arguments(self, parser):
        parser.add_argument('repo', help='repository name')
        parser.add_argument('branch', help='branch name')
        parser.add_argument('file', help='file name')
        parser.add_argument('logtype', help='log type (code or config)')
        parser.add_argument('runstatus', help='run status')

    def handle(self, *args, **options):

        #if len(args) < 4: raise CommandError('usage: <repo name> <branch> <file> <run_status>')

        br = Branch.objects.get(repo__name__exact=options['repo'], name__exact=options['branch'])
        if not br: raise CommandError("invalid repo/branch")
        br.run_status = options['runstatus']
        br.save()
        
        brlog = BranchLog()
        
        try:
            brlog = BranchLog.objects.get(branch=br, logtype=options['logtype'])
        except ObjectDoesNotExist:
            brlog.branch = br
            brlog.logtype = options['logtype']

        lastlog = 'From ' + options['file'] + '<br/>'
        
        for line in fileinput.input(options['file']):
            lastlog += line + '<br/>'
            
        if len(lastlog) > 20000:
            lastlog = lastlog[len(lastlog) - 20000:]
        brlog.lastlog = lastlog
        brlog.save()
