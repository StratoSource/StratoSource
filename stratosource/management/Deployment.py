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
import logging
import logging.config
from stratosource.models import Story, Branch, DeployableObject
from stratosource.management import Utils
import subprocess
import os
from zipfile import ZipFile, ZIP_DEFLATED
from lxml import etree



__author__="masmith"
__date__ ="$Sep 22, 2010 2:11:52 PM$"

typeMap = {'fields': 'CustomField','validationRules': 'ValidationRule',
           'listViews': 'ListView','namedFilters': 'NamedFilter',
           'searchLayouts': 'SearchLayout','recordTypes': 'RecordType',
           'objects': 'CustomObject', 'classes' : 'ApexClass', 'labels' : 'CustomLabel',
           'triggers': 'ApexTrigger', 'layouts': 'Layout',
            'pages': 'ApexPage', 'weblinks': 'CustomPageWebLink',
            'components': 'ApexComponent'}
SF_NAMESPACE='{http://soap.sforce.com/2006/04/metadata}'
_API_VERSION = "37.0"


def createFileCache(map):
    cache = {}
    for type,list in map.items():
        for object in list:
            path = os.path.join('unpackaged',type,object.filename)
            if os.path.exists(path):
                f = open(path)
                cache[object.filename] = f.read()
                f.close()
    return cache

def findXmlNode(doc, object, subtype = None):

    if object.type == 'objectTranslation':
        nodeName = SF_NAMESPACE + 'fields'
        nameKey = SF_NAMESPACE + 'name'
    if object.type == 'labels':
        nodeName = SF_NAMESPACE + 'labels'
        nameKey = SF_NAMESPACE + 'fullName'
    elif object.type == 'translationChange':
        nodeName = SF_NAMESPACE + 'fields'
        nameKey = SF_NAMESPACE + 'name'
    elif object.el_type == 'listViews':
        nodeName = SF_NAMESPACE + 'listViews'
        nameKey = SF_NAMESPACE + 'fullName'
    elif object.el_type == 'recordTypes':
        nodeName = SF_NAMESPACE + 'recordTypes'
        nameKey = SF_NAMESPACE + 'fullName'
    elif not subtype is None:
        nodeName = SF_NAMESPACE + subtype
        nameKey = SF_NAMESPACE + 'fullName'
    else:
        nodeName = SF_NAMESPACE + 'fields'
        nameKey = SF_NAMESPACE + 'fullName'

    children = doc.findall(nodeName)
    for child in children:
        node = child.find(nameKey)
        #print 'el_name=' + object.el_name
        #print 'node name=' + node.text
        if node is not None and node.text == object.el_name:
            return etree.tostring(child)
    return None

#
# this is an exception to the usual pattern of 2-level-deep xml nodes
#
def findXmlSubnode(doc, object):
    if object.type == 'objects':
        node_names = object.el_name.split(':')
        print('>>> node_names[0] = %s, node_names[1] = %s' % (node_names[0], node_names[1]))
        print('>>> subtype=' + object.el_subtype)
        children = doc.findall(SF_NAMESPACE + object.el_type)
        print('>>> looking for ' + object.el_type)
        for child in children:
#            print '>>> processing child'
            node = child.find(SF_NAMESPACE + 'fullName')
            if node is not None:
#                print '>>> processing node ' + node.text
#                print '>>> comparing [%s] to [%s]' % (node.text, node_names[0])
                if node.text == node_names[0]:
                    if object.el_subtype == 'picklists':
                        plvalues = child.findall(SF_NAMESPACE + 'picklistValues')
                        for plvalue in plvalues:
#                            print '>>> processing plvalue'
                            if plvalue.find(SF_NAMESPACE + 'picklist').text == node_names[1]:
#                                print '>>> plvalue found'
                                #
                                # due to difficulty we have to return everything from the root node
                                #
                                return etree.tostring(child)
    else:
        
        logging.getLogger('deploy').info('Unknown object type: ' + object.type)
    return None

def findChanges(doc, filename, cache, objects):

    doc = etree.XML(cache[filename])
    buf = ''
    for object in objects:
        if object.status == 'd': return None
        print('looking for name=%s, type=%s' % (object.el_name, object.el_type))
        if object.el_name.find(':') >= 0:
            # recordType node
            xml = findXmlSubnode(doc, object)
        else:
            xml = findXmlNode(doc, object)

        if not xml:
            logging.getLogger('deploy').info("Did not find XML node for %s.%s.%s.%s" % (object.filename,object.el_type,object.el_name,object.el_subtype))
            return None
        xml.append(buf)

    return xml


def getMetaForFile(filename):
    with open(filename+'-meta.xml', 'r') as f:
        return f.read()

def hasDuplicate(objectlist, obj):
    for o in objectlist:
        if o.el_name == obj.el_name and o.el_subtype == obj.el_subtype and o.filename == obj.filename:
            logger = logging.getLogger('deploy')
            logger.info('Rejected duplicate ' + obj.filename + '/' + obj.el_name)
            return True
    return False

def generatePackage(objectList, from_branch, to_branch,  retain_package,  packagedir):
    global cache

    logger = logging.getLogger('deploy')

    defaultNS = { None: 'http://soap.sforce.com/2006/04/metadata'}
    doc = etree.Element('Package', nsmap=defaultNS)
    etree.SubElement(doc, 'version').text = "{0}".format(_API_VERSION)

    if retain_package:
        output_name = os.path.join(packagedir,  'deploy_%s_%s.zip' % (from_branch.name, to_branch.name))
    else:
        output_name = '/tmp/deploy_%s_%s.zip' % (from_branch.name, to_branch.name)
    myzip = ZipFile(output_name, 'w', compression=ZIP_DEFLATED)

    logger.info('building %s', output_name)
    # create map and group by type
    map = {}
    for object in objectList:
        if not map.has_key(object.type): map[object.type] = []
        olist = map[object.type]
        if not hasDuplicate(olist, object): olist.append(object)
    cache = createFileCache(map)
    
    #objectPkgMap = {}   # holds all nodes to be added/updated, keyed by object/file name

    #labelchanges = ''
    for type,itemlist in map.items():
        if not typeMap.has_key(type):
            logger.error('** Unhandled type {0} - skipped'.format(type))
            continue

        logger.info('PROCESSING TYPE %s', type)

        if type == 'objects':
            registerObjectChanges(doc, cache, itemlist, myzip)
        elif type == 'labels':
            registerLabelChanges(doc, cache, itemlist, myzip)
        elif type in ['pages','classes','triggers']:
            registerCodeChanges(doc, type, itemlist, cache, myzip)
        elif type == 'layouts':
            writeLayoutDefinitions(doc, type, itemlist, cache, myzip)
        else:
            logger.warn('Type not supported: %s' % type)

    #if len(labelchanges) > 0:
        #writeLabelDefinitions(obj.filename, labelchanges, myzip)

    #writeObjectDefinitions(to_branch.repo, doc,  objectPkgMap, cache, myzip)

    xml = etree.tostring(doc, xml_declaration=True, encoding='UTF-8', pretty_print=True)
    myzip.writestr('package.xml', xml)

    myzip.close()
    return output_name


def registerLabelChanges(doc, cache, members, zipfile):

    fragments = findChanges(doc, 'CustomLabels.labels', cache, [member for member in members if member.status != 'd'])
    writeLabelDefinitions('CustomLabels.labels', fragments, zipfile)

    #
    # add only the requested labels to package.xml
    #
    el = etree.SubElement(doc, 'types')
    etree.SubElement(el, 'name').text = typeMap['labels']
    for member in members:
        if member.status == 'd':
            continue
        etree.SubElement(el, 'members').text = member.el_name

def registerObjectChanges(packagedoc, cache, members, zipfile):
    logger = logging.getLogger('deploy')

    objectPkgMap = {}   # holds all nodes to be added/updated, keyed by object/file name

    newdocs = {}

    #
    # build a map by object
    #
    for member in members:
        if member.status == 'd':
            continue
        if member.el_name is None:
            continue

        if not objectPkgMap.has_key(member.filename):
            objectPkgMap[member.filename] = []
        changes = objectPkgMap[member.filename]
        changes.append(member)

    #
    # separate out the types
    #
    fieldMap = {}
    listviewMap = {}
    validationruleMap = {}
    field_found = listview_found = validationrules_found = False
    for filename,items in objectPkgMap.items():
        m = [item for item in items if item.el_type == 'fields']
        if len(m) > 0:
            fieldMap[filename] = m
            field_found = True

        m = [item for item in items if item.el_type == 'listViews']
        if len(m) > 0:
            listviewMap[filename] = m
            listview_found = True

        m = [item for item in items if item.el_type == 'validationRules']
        if len(m) > 0:
            validationruleMap[filename] = m
            validationrules_found = True

    if field_found:
        #
        # FIELDS
        #
        types_el = etree.SubElement(packagedoc, 'types')
        etree.SubElement(types_el, 'name').text = typeMap['fields']
        for filename,fields in fieldMap.items():
            object_name = filename[0:filename.find('.')]
            #
            # add members to package.xml
            #
            for field in fields:
                etree.SubElement(types_el, 'members').text = object_name + '.' + field.el_name

            #
            # now dice up the object definition by removing all fields we are not deploying
            #
            newdoc = etree.XML(cache[filename]) if filename not in newdocs else newdocs[filename]
            newdocs[filename] = newdoc
            remove_inapplicable_elements(newdoc, fields, SF_NAMESPACE + 'fields')

    if listview_found:
        #
        # LISTVIEWS
        #
        types_el = etree.SubElement(packagedoc, 'types')
        etree.SubElement(types_el, 'name').text = typeMap['listViews']
        for filename,listviews in listviewMap.items():
            object_name = filename[0:filename.find('.')]
            #
            # add members to package.xml
            #
            for listview in listviews:
                etree.SubElement(types_el, 'members').text = object_name + '.' + listview.el_name

            #
            # now dice up the object definition by removing all fields we are not deploying
            #
            newdoc = etree.XML(cache[filename]) if filename not in newdocs else newdocs[filename]
            newdocs[filename] = newdoc
            remove_inapplicable_elements(newdoc, listviews, SF_NAMESPACE + 'listViews')

    if validationrules_found:
        #
        # VALIDATION RULES
        #
        slice_and_dice(packagedoc, cache, validationruleMap, 'validationRules', newdocs)


    for filename,newdoc in newdocs.items():
        writeObjectDefinition(filename, newdoc, zipfile)


def slice_and_dice(packagedoc, cache, maps, element_name, newdocs):
    types_el = etree.SubElement(packagedoc, 'types')
    etree.SubElement(types_el, 'name').text = typeMap[element_name]
    for filename, items in maps.items():
        object_name = filename[0:filename.find('.')]
        #
        # add members to package.xml
        #
        for item in items:
            etree.SubElement(types_el, 'members').text = object_name + '.' + item.el_name

        #
        # now dice up the object definition by removing all fields we are not deploying
        #
        newdoc = etree.XML(cache[filename]) if filename not in newdocs else newdocs[filename]
        newdocs[filename] = newdoc
        remove_inapplicable_elements(newdoc, items, SF_NAMESPACE + element_name)


def remove_inapplicable_elements(newdoc, items, element_name):
    deploy = [item.el_name for item in items]
    for child in newdoc.findall(element_name):
        node = child.find('fullName')
        if node is not None and node.text not in deploy:
            newdoc.remove(child)


def registerChange(doc, member, filetype):
    logger = logging.getLogger('deploy')

    el = etree.SubElement(doc, 'types')
    object_name = member.filename[0:member.filename.find('.')]
    if member.el_name is None:
        etree.SubElement(el, 'members').text = object_name
        etree.SubElement(el, 'name').text = typeMap[filetype]
        logger.info('registering: %s', object_name)
    else:
        el_name = member.el_name
        if filetype == 'objects':
            if member.el_type == 'recordTypes':
                filetype = 'recordTypes'
            elif el_name.find(':') > 0:
                el_name = el_name.split(':')[0]
                filetype = 'recordTypes'
            else:
                filetype = 'fields'
        if filetype == 'labels':
            etree.SubElement(el, 'members').text = el_name
        else:
            etree.SubElement(el, 'members').text = object_name + '.' + el_name
        etree.SubElement(el, 'name').text = typeMap[filetype]
        logger.info('registering: %s - %s', object_name + '.' + el_name, typeMap[filetype])

def writeLayoutDefinitions(packageDoc, filetype, filelist, cache, zipfile):
    logger = logging.getLogger('deploy')
    for member in filelist:
        print('member filename=%s, el_type=%s' % (member.filename, member.el_type))
        if member.filename.find('.') > 0:
            object_name = member.filename[0:member.filename.find('.')]
        if os.path.isfile(os.path.join('unpackaged',filetype,member.filename)):
            zipfile.writestr(filetype+'/'+member.filename, cache.get(member.filename))
            registerChange(packageDoc, member, filetype)
            logger.info('storing: %s', member.filename)

def registerCodeChanges(packageDoc, filetype, filelist, cache, zipfile):
    logger = logging.getLogger('deploy')
    names_for_package = []
    for member in filelist:
        print('member filename=%s, el_type=%s' % (member.filename, member.el_type))
        if member.filename.find('.') > 0:
            object_name = member.filename[0:member.filename.find('.')]
            names_for_package.append(object_name)
        ## !! assumes the right-side branch is still current in git !!
        if member.filename in cache:
            zipfile.writestr(filetype+'/'+member.filename, cache.get(member.filename))
            zipfile.writestr(filetype+'/'+member.filename+'-meta.xml', getMetaForFile(os.path.join('unpackaged',filetype,member.filename)))
            logger.info('storing: %s', member.filename)

    #
    # add entries to package.xml
    #
    el = etree.SubElement(packageDoc, 'types')
    for name in names_for_package:
        etree.SubElement(el, 'members').text = name
    etree.SubElement(el, 'name').text = typeMap[filetype]


def writeLabelDefinitions(filename, element, zipfile):
    xml = '<?xml version="1.0" encoding="UTF-8"?>'\
            '<CustomLabels xmlns="http://soap.sforce.com/2006/04/metadata">'
    xml += element
    xml += '</CustomLabels>'
    zipfile.writestr('labels/'+filename, xml)

def writeObjectDefinition(filename, doc,  zipfile):

    xml = etree.tostring(doc, xml_declaration=True, encoding='UTF-8', pretty_print=True)
    zipfile.writestr('objects/' + filename, xml)


def resetLocalRepo(branch_name):
    subprocess.check_call(["git","checkout",branch_name])
#    subprocess.check_call(["git","reset","--hard","{0}".format(branch_name)])

def deploy(objectList, from_branch, to_branch,  testOnly = False,  retain_package = False,  packagedir = '/tmp'):
    if packagedir == None: packagedir = '/tmp'
    os.chdir(from_branch.repo.location)
    resetLocalRepo(from_branch.name)
    for object in objectList:
        print(object.status, object.filename, object.type, object.el_name, object.el_subtype)
    output_name = generatePackage(objectList, from_branch, to_branch,  retain_package,  packagedir)
    agent = Utils.getAgentForBranch(to_branch, logger=logging.getLogger('deploy'));
    results = agent.deploy(output_name,  testOnly)
    if not retain_package: os.unlink(output_name);
    return results

#
# External entry point
#

def deployPackage(pkgStatus):
    deployPkg = pkgStatus.package
    to_branch = pkgStatus.target_environment
    
    results = deploy(   deployPkg.deployable_objects.all(),
                                  deployPkg.source_environment,
                                  to_branch,
                                  testOnly = pkgStatus.test_only,
                                  retain_package = pkgStatus.keep_package,
                                  packagedir = pkgStatus.package_location)
    logtext = ''
    passed = True

    pkgStatus.result = 'i'
    pkgStatus.save()

    if results is not None:
        if not results.success:
            for dm in results.messages:
                if not dm.success:
                    passed = False
                    logtext += 'fail: {0} - {1} <br />\n'.format(dm.fullName, dm.problem)
                else:
                    logtext += 'ok: {0} <br />\n'.format(dm.fullName)
    else:
        logtext = 'deployment results not available'

    pkgStatus.log_output = logtext
    pkgStatus.result = 's' if passed else 'f'
    pkgStatus.save()
