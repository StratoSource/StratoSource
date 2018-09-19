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

from django.core.management.base import BaseCommand, CommandError

from stratosource.management.labels import generateLabelSpreadsheet
from stratosource.models import Release, Repo


__author__="masmith"
__date__ ="$Nov 8, 2012 11:14:00 AM$"


class Command(BaseCommand):

    def handle(self, *args, **options):
        if len(args) < 2: raise CommandError('usage: labels <repo> <release name>')

        repo = Repo.objects.get(name=args[0])
        release = Release.objects.get(name=args[1])
        generateLabelSpreadsheet(repo, release.id)

