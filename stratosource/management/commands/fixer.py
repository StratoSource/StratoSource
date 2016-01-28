from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ObjectDoesNotExist
from stratosource.admin.models import Branch, Commit, Delta, TranslationDelta, DeployableObject
import subprocess
import popen2
from datetime import datetime
import os

class Command(BaseCommand):

    def handle(self, *args, **options):

        if len(args) < 2: raise CommandError('usage: <repo name> <branch>')

        br = Branch.objects.get(repo__name__exact=args[0], name__exact=args[1])
        if not br: raise CommandException("invalid repo/branch")

        dolist = DeployableObject.objects.filter(branch=br).order_by('filename','status')
        domap = {}
        for dobj in dolist:
            if not domap.has_key(dobj.filename): domap[dobj.filename] = []
            domap[dobj.filename].append(dobj)
        for filename,recs in domap.items():
            if len(recs) > 1:
                print '%s  %d' % (filename, len(recs))

