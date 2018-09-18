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
#    but WITHOUT ANY WARRANTY; without even the implied waarranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with StratoSource.  If not, see <http://www.gnu.org/licenses/>.
#
from django.core.management.base import BaseCommand
from django.core.exceptions import ObjectDoesNotExist
import os
import sys
import subprocess
import logging
from datetime import datetime
from django.db import transaction
from lxml import etree
import stratosource.models

__author__ = "masmith"
__date__ = "$Jul 26, 2010 2:23:44 PM$"

SF_NAMESPACE = '{http://soap.sforce.com/2006/04/metadata}'
CODE_BASE = 'unpackaged'

documentCache = {}
mapCache = {}

logger = logging.getLogger('console')


class NewObjectException(Exception):
    pass


class DeletedObjectException(Exception):
    pass


##
# [ git utilities ]
##

def resetLocalRepo(branch_name):
    subprocess.check_call(["git", "checkout", branch_name])


#    subprocess.check_call(["git","reset","--hard","{0}".format(branch_name)])

def branchExists(branchname):
    proc = subprocess.Popen(['git', 'branch', '-a'], shell=False, stdout=subprocess.PIPE)
    input, error = proc.communicate()
    lines = input.decode('utf-8').split('\n')
    for br in lines:
        br = br.rstrip()
        if len(br) > 0 and br[2:] == branchname: return True
    return False


def getCurrentTag():
    proc = subprocess.Popen(['git', 'describe'], shell=False, stdout=subprocess.PIPE)
    inp, error = proc.communicate()
    tag = inp.rstrip()
    return tag.decode('utf-8')


def getCurrentBranch():
    proc = subprocess.Popen(['git', 'branch'], shell=False, stdout=subprocess.PIPE)
    input, error = proc.communicate()
    lines = input.decode('utf-8').split('\n')
    for br in lines:
        br = br.rstrip()
        if len(br) > 0 and br[0:2] == "* ":
            return br[2:]
    return 'unknown'


def verifyGitRepo():
    proc = subprocess.Popen(['git', 'status'], shell=False, stderr=subprocess.PIPE)
    input, error = proc.communicate()
    error = error.decode('utf-8')
    if error.find('Not a git repository') > 0:
        logger.error('Error: Not a git repository')
        sys.exit(1)


def getDiffNames(left, right):
    logger.info('git diff --name-only %s %s' % (left, right))
    proc = subprocess.Popen(['git', 'diff', '--name-only', left, right], shell=False, stdout=subprocess.PIPE)
    input, error = proc.communicate()
    changedList = []
    all = 0
    map = {}
    lines = input.decode('utf-8').split('\n')
    for entry in lines:
        all = all + 1
        entry = entry.rstrip()
        if entry == '.gitignore': continue
        if len(entry) > 1 and not entry.endswith('.xml'):
            # logger.debug('  entry={0}'.format(entry))
            parts = entry.split('/')
            typ = parts[1]
            name = '/'.join(parts[2:])  # put trailing components back together to support folder-based assets
            #            a, b = os.path.split(entry)
            if typ not in map:
                map[typ] = []
            map[typ].append(name)
            changedList.append(entry)

    changedList.sort()
    return map


##
# [ XML parsing and searching ]
##

def getElementMap(key):
    global mapCache

    if key in mapCache:
        return mapCache[key]
    m = {}
    mapCache[key] = m
    return m


def getObjectChanges(lkey, lcache, rkey, rcache, objectName, elementName, resolver):
    global documentCache

    ldoc = None
    rdoc = None

    if lkey + objectName in documentCache:
        ldoc = documentCache[lkey + objectName]
    if rkey + objectName in documentCache:
        rdoc = documentCache[rkey + objectName]

    rmap = getElementMap(rkey + objectName + elementName)
    lmap = getElementMap(lkey + objectName + elementName)

    if ldoc is None:
        lobj = lcache.get(objectName)
        if lobj:
            ldoc = etree.XML(lobj)
            if ldoc is None:
                return None, None
            documentCache[lkey + objectName] = ldoc
    if rdoc is None:
        robj = rcache.get(objectName)
        if robj:
            rdoc = etree.XML(robj)
            if rdoc is None:
                return None, None
            documentCache[rkey + objectName] = rdoc

    if ldoc is None and rdoc is not None:
        raise NewObjectException()
    if ldoc is not None and rdoc is None:
        raise DeletedObjectException()

    return resolver(ldoc, rdoc, rmap, lmap, elementName)


def compareObjectMaps(lmap, rmap):
    missing = {}
    updates = {}

    for lname, lnodestring in lmap.items():
        # find the field in the other file
        if lname in rmap:
            rnodestring = rmap[lname]
            # compare for changes
            if lnodestring != rnodestring:
                updates[lname] = rnodestring
        else:
            # field missing on right, must be deleted
            missing[lname] = lnodestring
    return updates, missing


def populateElementMap(doc, nodeName, elementName, amap):
    if doc != None and len(amap) == 0:
        children = doc.findall(nodeName)
        for child in children:
            node = child.find(elementName)
            amap[node.text] = etree.tostring(child)


def objectChangeResolver(ldoc, rdoc, rmap, lmap, elementName):
    nodeName = SF_NAMESPACE + elementName
    nameKey = SF_NAMESPACE + 'fullName'
    #
    # build a map of custom label names and xml fragment for faster lookups
    #
    populateElementMap(rdoc, nodeName, nameKey, rmap)
    populateElementMap(ldoc, nodeName, nameKey, lmap)
    return compareObjectMaps(lmap, rmap)


def objectTranslationChangeResolver(ldoc, rdoc, rmap, lmap, elementName):
    nodeName = SF_NAMESPACE + elementName
    nameKey = SF_NAMESPACE + 'name'
    #
    # build a map of custom label names and xml fragment for faster lookups
    #
    populateElementMap(rdoc, nodeName, nameKey, rmap)
    populateElementMap(ldoc, nodeName, nameKey, lmap)
    return compareObjectMaps(lmap, rmap)


def translationChangeResolver(ldoc, rdoc, rmap, lmap, elementName):
    nodeName = SF_NAMESPACE + elementName
    nameKey = SF_NAMESPACE + 'name'
    #
    # build a map of custom label names and xml fragment for faster lookups
    #
    populateElementMap(rdoc, nodeName, nameKey, rmap)
    populateElementMap(ldoc, nodeName, nameKey, lmap)
    return compareObjectMaps(lmap, rmap)


def getAllFullNames(doc, elementName, tagname='fullName'):
    fqfullname = SF_NAMESPACE + tagname
    nodes = doc.findall(SF_NAMESPACE + elementName)
    if nodes:
        allnames = []
        for node in nodes:
            el = node.find(fqfullname)
            if el is not None: allnames.append(el.text)
        # allnames = [node.find(fqfullname).text for node in nodes]
        return allnames
    else:
        logger.debug('No nodes found for %s' % elementName)
    return []


def getAllObjectChanges(objectName, lFileCache, rFileCache, elementname, resolver):
    updates, deletes = getObjectChanges('l', lFileCache, 'r', rFileCache, objectName, elementname, resolver)
    rupdates, inserts = getObjectChanges('r', rFileCache, 'l', lFileCache, objectName, elementname, resolver)
    return inserts, updates, deletes


##
# [ database and caching ]
##

def createFileCache(hash, map, branch_name):
    subprocess.check_call(["git", "checkout", branch_name])

    try:
        tmpbranch = branch_name + '_sfdiff'
        if branchExists(tmpbranch):
            subprocess.check_call(["git", "branch", "-D", tmpbranch])
        subprocess.check_call(["git", "checkout", "-b", tmpbranch, hash])

        #    os.system('git reset --hard {0}'.format(hash))
        cache = {}
        for type, list in map.items():
            if type in ('objects', 'labels', 'translations', 'objectTranslations', 'workflows'):
                for objectName in list:
                    try:
                        path = os.path.join(CODE_BASE, type, objectName)
                        f = open(path, 'rb')
                        cache[objectName] = f.read()
                        f.close()
                    except IOError:
                        # print '** not able to load ' + path
                        pass  # caused by a new file added, not present on current branch
            else:
                for objectName in list:
                    if os.path.isfile(os.path.join(CODE_BASE, type, objectName)):
                        cache[objectName] = None
        return cache
    finally:
        subprocess.check_call(["git", "checkout", branch_name])


def getDeployable(branch, objectName, objectType, el_type, el_name, el_subtype=None):
    try:
        if el_type and el_name:
            deployable = stratosource.models.DeployableObject.objects.get(branch=branch, type__exact=objectType,
                                                                          filename__exact=objectName,
                                                                          el_type__exact=el_type,
                                                                          el_name__exact=el_name,
                                                                          el_subtype__exact=el_subtype,
                                                                          status__exact='a')
        else:
            deployable = stratosource.models.DeployableObject.objects.get(branch=branch, type__exact=objectType,
                                                                          filename__exact=objectName,
                                                                          status__exact='a')
    except ObjectDoesNotExist:
        deployable = stratosource.models.DeployableObject()
        deployable.type = objectType
        deployable.filename = objectName
        deployable.branch = branch
        deployable.el_type = el_type
        deployable.el_name = el_name
        deployable.el_subtype = el_subtype
        deployable.save()
    return deployable


def insert_deltas(commit, objectName, type, items, delta_type, el_type, el_subtype=None):
    #    global mqclient

    for item in items:
        deployable = getDeployable(commit.branch, objectName, type, el_type, item, el_subtype)
        delta = stratosource.models.Delta()
        delta.user_change = get_last_change(objectName, el_type, item)
        delta.object = deployable
        delta.commit = commit
        delta.delta_type = delta_type
        delta.save()


# if not delta.user_change is None:
#            mqclient.publish({'user': delta.user_change.sfuser.name.encode('ascii', 'ignore'), 'commit': commit.hash,
#                              'dtype': delta_type, 'type': type, 'item': item,
#                              'last_update': delta.user_change.last_update.isoformat()})


def get_last_change(objectName, el_type, el_name):
    fullName = objectName
    if el_type == 'labels':
        return None  # not doing audit tracking for labels

    if el_type == 'fields':
        el_type = 'object'

    parts = objectName.split('.')
    if len(parts) > 1 and el_type is not None:
        parts[0] = el_type + ':' + parts[0]
        if el_name: parts[0] += '.' + el_name
        fullName = parts[0]  # '.'.join(parts)
    # print ' fullName=%s' % fullName

    lastchangelist = list(
        stratosource.models.UserChange.objects.filter(branch=working_branch, apex_name=fullName).order_by(
            '-last_update'))
    if len(lastchangelist) > 0:
        return lastchangelist[0]
    return None


def getDeployableTranslation(branch, label, locale):
    try:
        deployableT = stratosource.models.DeployableTranslation.objects.get(branch=branch, label=label, locale=locale,
                                                                            status__exact='a')
    except ObjectDoesNotExist:
        deployableT = stratosource.models.DeployableTranslation()
        deployableT.label = label
        deployableT.locale = locale
        deployableT.branch = branch
        deployableT.save()
    return deployableT


def insertTranslationDeltas(commit, items, delta_type, locale):
    for item in items:
        deployableT = getDeployableTranslation(commit.branch, item, locale)
        delta = stratosource.models.TranslationDelta()
        delta.translation = deployableT
        delta.commit = commit
        delta.delta_type = delta_type
        delta.save()


##
# [ objects ]
##
def analyze_object_changes(alist, lFileCache, rFileCache, elementname, commit):
    global documentCache

    changesFound = False
    for objectName in alist:
        logger.debug('analyzing %s > %s' % (objectName, elementname))
        try:
            inserts, updates, deletes = getAllObjectChanges(objectName, lFileCache, rFileCache, elementname,
                                                            objectChangeResolver)
            if (inserts and len(inserts)) or (updates and len(updates)) or (deletes and len(deletes)):
                if inserts:
                    insert_deltas(commit, objectName, 'objects', inserts.keys(), 'a', elementname)
                if updates:
                    insert_deltas(commit, objectName, 'objects', updates.keys(), 'u', elementname)
                if deletes:
                    insert_deltas(commit, objectName, 'objects', deletes.keys(), 'd', elementname)
                changesFound = True

        except NewObjectException:
            logger.debug('New object %s' % objectName)
            doc = documentCache['r' + objectName]
            insert_deltas(commit, objectName, 'objects', getAllFullNames(doc, elementname), 'a', elementname)

        except DeletedObjectException:
            doc = documentCache['l' + objectName]
            insert_deltas(commit, objectName, 'objects', getAllFullNames(doc, elementname), 'd', elementname)

    if not changesFound:
        pass


##
# [ objectTranslation ]
##
def analyze_object_translation_changes(list, lFileCache, rFileCache, elementname, commit):
    global documentCache

    changesFound = False
    for objectName in list:
        try:
            inserts, updates, deletes = getAllObjectChanges(objectName, lFileCache, rFileCache, elementname,
                                                            objectTranslationChangeResolver)
            if (inserts and len(inserts) > 0) or (updates and len(updates) > 0) or (deletes and len(deletes) > 0):
                if inserts:
                    insert_deltas(commit, objectName, 'objectTranslations', inserts.keys(), 'a', elementname)
                if updates:
                    insert_deltas(commit, objectName, 'objectTranslations', updates.keys(), 'u', elementname)
                if deletes:
                    insert_deltas(commit, objectName, 'objectTranslations', deletes.keys(), 'd', elementname)
                changesFound = True

        except NewObjectException:
            doc = documentCache['r' + objectName]
            insert_deltas(commit, objectName, 'objectTranslations', getAllFullNames(doc, elementname), 'a', elementname)
            return

        except DeletedObjectException:
            doc = documentCache['l' + objectName]
            insert_deltas(commit, objectName, 'objectTranslations', getAllFullNames(doc, elementname), 'd', elementname)
            return

    if not changesFound:
        pass


##
# [ labels ]
##
def analyze_label_changes(alist, lFileCache, rFileCache, elementname, commit):
    global documentCache

    for objectName in alist:
        try:
            inserts, updates, deletes = getAllObjectChanges(objectName, lFileCache, rFileCache, elementname,
                                                            objectChangeResolver)
            if (inserts and len(inserts)) or (updates and len(updates)) or (deletes and len(deletes)):
                if inserts:
                    insert_deltas(commit, objectName, 'labels', inserts.keys(), 'a', elementname)
                if updates:
                    insert_deltas(commit, objectName, 'labels', updates.keys(), 'u', elementname)
                if deletes:
                    insert_deltas(commit, objectName, 'labels', deletes.keys(), 'd', elementname)

        except NewObjectException:
            doc = documentCache['r' + objectName]
            insert_deltas(commit, objectName, 'labels', getAllFullNames(doc, elementname), 'a', elementname)

        except DeletedObjectException:
            doc = documentCache['l' + objectName]
            insert_deltas(commit, objectName, 'labels', getAllFullNames(doc, elementname), 'd', elementname)


##
# [ translations ]
##
def analyze_translation_changes(alist, lFileCache, rFileCache, commit):
    global documentCache

    for objectName in alist:
        locale = objectName[:-12]  # the locale is part of the object name
        try:
            inserts, updates, deletes = getAllObjectChanges(objectName, lFileCache, rFileCache, 'customLabels',
                                                            translationChangeResolver)
            if (inserts and len(inserts)) or (updates and len(updates)) or (deletes and len(deletes)):
                if inserts:
                    insertTranslationDeltas(commit, inserts.keys(), 'a', locale)
                if updates:
                    insertTranslationDeltas(commit, updates.keys(), 'u', locale)
                if deletes:
                    insertTranslationDeltas(commit, deletes.keys(), 'd', locale)

        except NewObjectException:
            doc = documentCache['r' + objectName]
            insert_deltas(commit, objectName, 'translations', getAllFullNames(doc, 'customLabels', tagname='name'), 'a',
                          'customLabels')

        except DeletedObjectException:
            doc = documentCache['l' + objectName]
            insert_deltas(commit, objectName, 'translations', getAllFullNames(doc, 'customLabels', tagname='name'), 'd',
                          'customLabels')


##
# [ record types/picklists ]
##

def recTypePicklistResolver(ldoc, rdoc, rmap, map, elementName):
    missing = {}
    updates = {}
    inserts = {}

    if ldoc is None:
        lnodes = []
    else:
        lnodes = ldoc.findall(SF_NAMESPACE + elementName)
    if rdoc is None:
        rnodes = []
    else:
        rnodes = rdoc.findall(SF_NAMESPACE + elementName)

    #
    # put the left and right lists in a hash for easier analysis
    #
    fqfullname = SF_NAMESPACE + 'fullName'
    fqpicklistvalues = SF_NAMESPACE + 'picklistValues'
    fqpicklist = SF_NAMESPACE + 'picklist'

    llists = {}
    for lnode in lnodes:
        fullName = lnode.find(fqfullname).text
        lpicklists = lnode.findall(fqpicklistvalues)
        for lpicklist in lpicklists:
            lpicklist_name = lpicklist.find(fqpicklist).text
            llists[fullName + ':' + lpicklist_name] = etree.tostring(lpicklist)

    rlists = {}
    for rnode in rnodes:
        fullName = rnode.find(fqfullname).text
        rpicklists = rnode.findall(fqpicklistvalues)
        for rpicklist in rpicklists:
            rpicklist_name = rpicklist.find(fqpicklist).text
            rlists[fullName + ':' + rpicklist_name] = etree.tostring(rpicklist)

    #
    # go down the left side lookup for updates and deletes
    #
    for lrectype_name in llists.keys():
        if lrectype_name in rlists:
            if rlists[lrectype_name] != llists[lrectype_name]:
                updates[lrectype_name] = rlists[lrectype_name]
        else:
            missing[lrectype_name] = llists[lrectype_name]

    #
    # go down the right side looking for additions
    #
    for rrectype_name in rlists.keys():
        if not rrectype_name in llists:
            inserts[rrectype_name] = rlists[rrectype_name]

    return inserts, updates, missing


def analyze_recordtype_picklist_changes(list, lFileCache, rFileCache, commit):
    global documentCache

    for objectName in list:
        try:
            inserts, updates, deletes = getObjectChanges('l', lFileCache, 'r', rFileCache, objectName, 'recordTypes',
                                                         recTypePicklistResolver)
            if inserts:
                insert_deltas(commit, objectName, 'objects', inserts, 'a', 'recordTypes', 'picklists')
            if updates:
                insert_deltas(commit, objectName, 'objects', updates, 'u', 'recordTypes', 'picklists')
            if deletes:
                insert_deltas(commit, objectName, 'objects', deletes, 'd', 'recordTypes', 'picklists')

        except NewObjectException:
            doc = documentCache['r' + objectName]
            insert_deltas(commit, objectName, 'objects', getAllFullNames(doc, 'recordTypes', tagname='name'), 'a',
                          'recordTypes')

        except DeletedObjectException:
            doc = documentCache['l' + objectName]
            insert_deltas(commit, objectName, 'objects', getAllFullNames(doc, 'recordTypes', tagname='name'), 'd',
                          'recordTypes')


##
# [ workflows ]
##
def analyze_workflow_changes(list, lFileCache, rFileCache, elementname, commit):
    global documentCache

    changesFound = False
    for objectName in list:
        try:
            #            print'  object name is', objectName, 'element name is', elementname
            inserts, updates, deletes = getAllObjectChanges(objectName, lFileCache, rFileCache, elementname,
                                                            objectChangeResolver)
            if (inserts and len(inserts) > 0) or (updates and len(updates) > 0) or (deletes and len(deletes) > 0):
                if inserts:
                    insert_deltas(commit, objectName, 'workflows', inserts.keys(), 'a', elementname)
                if updates:
                    insert_deltas(commit, objectName, 'workflows', updates.keys(), 'u', elementname)
                if deletes:
                    insert_deltas(commit, objectName, 'workflows', deletes.keys(), 'd', elementname)
                changesFound = True

        except NewObjectException:
            doc = documentCache['r' + objectName]
            insert_deltas(commit, objectName, 'workflows', getAllFullNames(doc, elementname), 'a', elementname)

        except DeletedObjectException:
            doc = documentCache['l' + objectName]
            insert_deltas(commit, objectName, 'workflows', getAllFullNames(doc, elementname), 'd', elementname)

    if not changesFound:
        pass


@transaction.atomic
def analyze_commit(branch, commit):
    global documentCache
    global mapCache
    global working_branch
    global change_batch

    working_branch = branch

    logger.info("Analyzing commit %s" % commit.hash)

    documentCache = {}  # do not want to accumulate this stuff over multiple iterations
    mapCache = {}
    change_batch = None

    # clean up deltas in case we are rerunning
    stratosource.models.Delta.objects.filter(commit=commit).delete()
    stratosource.models.TranslationDelta.objects.filter(commit=commit).delete()

    lhash = commit.prev_hash
    rhash = commit.hash

    ##
    # call "git diff" to get a list of changed files
    ##
    omap = getDiffNames(lhash, rhash)

    ##
    # load all changed files from each hash into a map for performance (config only)
    ##
    lFileCache = createFileCache(lhash, omap, branch.name)
    rFileCache = createFileCache(rhash, omap, branch.name)

    for otype, olist in omap.items():
        #        logger.debug("Type: %s" % otype)
        if otype == 'objects':
            analyze_object_changes(olist, lFileCache, rFileCache, 'fields', commit)
            analyze_object_changes(olist, lFileCache, rFileCache, 'fieldSets', commit)
            analyze_object_changes(olist, lFileCache, rFileCache, 'validationRules', commit)
            analyze_object_changes(olist, lFileCache, rFileCache, 'webLinks', commit)
            analyze_object_changes(olist, lFileCache, rFileCache, 'recordTypes', commit)
            analyze_recordtype_picklist_changes(olist, lFileCache, rFileCache, commit)
            analyze_object_changes(olist, lFileCache, rFileCache, 'namedFilters', commit)
            analyze_object_changes(olist, lFileCache, rFileCache, 'listViews', commit)
            # misc single-node elements
        #                analyzeObjectChanges(list, lFileCache, rFileCache, 'label', commit)
        #                analyzeObjectChanges(list, lFileCache, rFileCache, 'nameField', commit, nameKey='label')
        #                analyzeObjectChanges(list, lFileCache, rFileCache, 'pluralLabel', commit)
        #                analyzeObjectChanges(list, lFileCache, rFileCache, 'searchLayouts', commit)
        #                analyzeObjectChanges(list, lFileCache, rFileCache, 'sharingModel', commit)

        elif otype == 'translations':
            analyze_translation_changes(olist, lFileCache, rFileCache, commit)

        elif otype == 'workflows':
            analyze_workflow_changes(olist, lFileCache, rFileCache, 'alerts', commit)
            analyze_workflow_changes(olist, lFileCache, rFileCache, 'fieldUpdates', commit)
            analyze_workflow_changes(olist, lFileCache, rFileCache, 'rules', commit)
            analyze_workflow_changes(olist, lFileCache, rFileCache, 'tasks', commit)

        elif otype == 'objectTranslations':
            analyze_object_translation_changes(olist, lFileCache, rFileCache, 'fields', commit)
            analyze_object_translation_changes(olist, lFileCache, rFileCache, 'validationRules', commit)
            analyze_object_translation_changes(olist, lFileCache, rFileCache, 'webLinks', commit)

        elif otype == 'labels':
            analyze_label_changes(olist, lFileCache, rFileCache, 'labels', commit)

        else:
            for listitem in olist:
                delta_type = None
                if listitem in lFileCache and listitem not in rFileCache:
                    delta_type = 'd'
                elif listitem not in lFileCache:
                    delta_type = 'a'
                else:
                    delta_type = 'u'

                delta = stratosource.models.Delta()
                delta.object = getDeployable(branch, listitem, otype, None, None, None)
                delta.commit = commit
                delta.user_change = get_last_change(listitem, None, None)
                if delta.user_change is None:
                    # logger.debug('** Audit record not found for %s' % listitem)
                    pass
                else:
                    # print 'audit record found!'
                    pass
                delta.delta_type = delta_type
                delta.save()
                logger.debug('  added delta for {0}'.format(listitem))
            #                if not delta.user_change is None:
            #                    print 'user %s' % (delta.user_change.sfuser.name,)
            #                    print 'commit %s' % (commit,)
            #                    print 'dtype %s' % (delta_type,)
            #                    print 'otype %s' % (otype,)
            #                    print 'item %s' % (listitem,)

            #                    mqclient.publish(
            #                            {'user': delta.user_change.sfuser.name.encode('ascii', 'ignore'), 'commit': commit.hash,
            #                             'dtype': delta_type, 'type': otype, 'item': listitem,
            #                             'last_update': delta.user_change.last_update.isoformat()})

    commit.status = 'c'
    commit.save()


def generate_analysis(branch, start_date):
    global documentCache

    commits = stratosource.models.Commit.objects.filter(branch=branch, status__exact='p', prev_hash__isnull=False,
                                                        date_added__gte=start_date).order_by('-date_added')

    for commit in commits:
        if commit.prev_hash is None or len(commit.prev_hash) == 0: continue
        analyze_commit(branch, commit)


# msg = AdminMessage()
#    msg.subject = branch.name + ' commits processed'
#    msg.body = '%d %s commits were processed on %s' % (len(commits), branch.name, str(datetime.now()))
#    msg.sender = 'sfdiff'
#    msg.save()

##
# [ Entry point ]
##

class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('repo', help='repository name')
        parser.add_argument('branch', help='branch name')

    def handle(self, *args, **options):
        global documentCache

        repo = stratosource.models.Repo.objects.get(name__exact=options['repo'])
        branch = stratosource.models.Branch.objects.get(repo=repo, name__exact=options['branch'])

        #        mqclient = MQClient(exch='delta')

        #        if len(args) == 3:
        #            start_date = datetime.strptime(args[2], '%m-%d-%Y')
        #        else:

        start_date = datetime(2000, 1, 1, 0, 0)  # , tzinfo=pytz.utc)

        os.chdir(os.path.join(repo.location, branch.name))

        ##
        # some basic housekeeping
        ##
        resetLocalRepo(branch.name)
        verifyGitRepo()

        generate_analysis(branch, start_date)

        documentCache = {}  # just in case running stateful by django middleware, clear out between calls

        # try to leave repo in a good state
        resetLocalRepo(branch.name)
