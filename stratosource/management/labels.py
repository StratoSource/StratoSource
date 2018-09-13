#    Copyright 2010, 2011, 2012 Red Hat Inc.
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
from stratosource.models import Release, Repo, DeployableObject
import os
from lxml import etree
import csv


__author__="masmith"
__date__ ="$Nov 8, 2012 11:14:00 AM$"

SF_NAMESPACE='{http://soap.sforce.com/2006/04/metadata}'
CODE_BASE = 'unpackaged'


def generateLabelSpreadsheet(branch, release_id):
        release = Release.objects.get(id=release_id)
        release_labels = []
        for story in release.stories.all():
            deployables = DeployableObject.objects.filter(pending_stories=story, el_type='labels')
            release_labels += [d.el_name for d in deployables]
        os.chdir(branch.repo.location)

        path = os.path.join(CODE_BASE, 'labels', 'CustomLabels.labels')
        f  = open(path)
        doc = etree.XML(f.read())
        f.close()
        
        labelmap = {}

        children = doc.findall(SF_NAMESPACE + 'labels')
        for child in children:
            labelName = child.find(SF_NAMESPACE + 'fullName').text
            if labelName in release_labels:
                if not labelmap.has_key(labelName): labelmap[labelName] = {}
                langmap = labelmap[labelName]
                langkey = child.find(SF_NAMESPACE + 'language').text
                desc = child.find(SF_NAMESPACE + 'value').text
                langmap[langkey] = desc
                print('label=%s, key=%s, desc=%s' % (labelName, langkey, desc))

        with open('/tmp/labels.csv', 'w') as csvfile:
            csvfile.write(['Key','en_US'])
            for labelkey, langmap in labelmap.items():
                for langkey, value in langmap.items():
                    if langkey == 'en_US':
                        csv.write([labelkey, value])
                    else:
                        csv.write([labelkey,''])
        f = open('/tmp/labels.csv')
        xls = f.read()
        return xls



