#    Copyright 2010, 2016 Red Hat Inc.
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
import json
import subprocess
from django.core.management.base import BaseCommand, CommandError
#from django.utils.log import getLogger
import logging
import time
import datetime
import os
from stratosource.models import Branch, BranchStats
from stratosource.management import Utils
from ss2.settings import LOGGING
from ss2.settings import USE_TZ

logger = logging.getLogger('console')


def code_stats(adir, pattern):
    files = os.listdir(adir)
    lines = 0
    bytes = 0
    filecnt = 0
    for f in files:
        if not f.endswith(pattern):
            continue
        filecnt += 1
        with open(os.path.join(adir, f), 'r') as tmp:
            buf = tmp.read()
            bytes += len(buf)
            lines += len(buf.split('\n'))
    return filecnt, lines, bytes


class Command(BaseCommand):
    args = ''
    help = 'calculate statistics'

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):

        branches = Branch.objects.filter(enabled__exact=True)
        stamp = str(int(time.time()))
        for branch in branches:
            try:
                os.chdir(branch.repo.location)
            except Exception:
                continue
            subprocess.check_call(["git", "checkout", branch.name])
            stats = {}
            stats['cls_files'], stats['cls_lines'], stats['cls_bytes'] =  code_stats(os.path.join(branch.repo.location, 'unpackaged/classes'), '.cls')
            stats['page_files'], stats['page_lines'], stats['page_bytes'] = code_stats(os.path.join(branch.repo.location, 'unpackaged/pages'), '.page')
            stats['trigger_files'], stats['trigger_lines'], stats['trigger_bytes'] = code_stats(os.path.join(branch.repo.location, 'unpackaged/triggers'), '.trigger')

            try:
                bs = BranchStats.objects.get(branch=branch)
            except Exception:
                bs = BranchStats()
            bs.branch = branch
            bs.cls_files = stats['cls_files']
            bs.cls_lines = stats['cls_lines']
            bs.cls_bytes = stats['cls_bytes']
            bs.page_files = stats['page_files']
            bs.page_lines = stats['page_lines']
            bs.page_bytes = stats['page_bytes']
            bs.trigger_files = stats['trigger_files']
            bs.trigger_lines = stats['trigger_lines']
            bs.trigger_bytes = stats['trigger_bytes']
            bs.files = bs.cls_files + bs.page_files + bs.trigger_files
            bs.lines = bs.cls_lines + bs.page_lines + bs.trigger_lines
            bs.bytes = bs.cls_bytes + bs.page_bytes + bs.trigger_bytes

            bs.save()
