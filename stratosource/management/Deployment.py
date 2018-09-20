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
from stratosource.management import Utils
import subprocess
import os
from zipfile import ZipFile, ZIP_DEFLATED
from lxml import etree

__author__ = "masmith"
__date__ = "$Sep 22, 2010 2:11:52 PM$"

typeMap = {'fields': 'CustomField', 'validationRules': 'ValidationRule',
           'listViews': 'ListView', 'namedFilters': 'NamedFilter',
           'searchLayouts': 'SearchLayout', 'recordTypes': 'RecordType',
           'objects': 'CustomObject', 'classes': 'ApexClass', 'labels': 'CustomLabel',
           'triggers': 'ApexTrigger', 'layouts': 'Layout',
           'pages': 'ApexPage', 'weblinks': 'CustomPageWebLink',
           'webLinks': 'WebLink', 'fieldSets': 'FieldSet',
           'components': 'ApexComponent', 'email': 'EmailTemplate'}
SF_NAMESPACE = '{http://soap.sforce.com/2006/04/metadata}'
_API_VERSION = "37.0"


def create_file_cache(map):
    thecache = {}
    for etype, itemlist in map.items():
        for object in itemlist:
            path = os.path.join('unpackaged', etype, object.filename)
            if os.path.exists(path):
                f = open(path)
                thecache[object.filename] = f.read()
                f.close()
    return thecache


def find_xml_node(doc, object, subtype=None):
    if object.type == 'objectTranslation':
        node_name = SF_NAMESPACE + 'fields'
        name_key = SF_NAMESPACE + 'name'
    if object.type == 'labels':
        node_name = SF_NAMESPACE + 'labels'
        name_key = SF_NAMESPACE + 'fullName'
    elif object.type == 'translationChange':
        node_name = SF_NAMESPACE + 'fields'
        name_key = SF_NAMESPACE + 'name'
    elif object.el_type == 'listViews':
        node_name = SF_NAMESPACE + 'listViews'
        name_key = SF_NAMESPACE + 'fullName'
    elif object.el_type == 'recordTypes':
        node_name = SF_NAMESPACE + 'recordTypes'
        name_key = SF_NAMESPACE + 'fullName'
    elif subtype is not None:
        node_name = SF_NAMESPACE + subtype
        name_key = SF_NAMESPACE + 'fullName'
    else:
        node_name = SF_NAMESPACE + 'fields'
        name_key = SF_NAMESPACE + 'fullName'

    children = doc.findall(node_name)
    for child in children:
        node = child.find(name_key)
        if node is not None and node.text == object.el_name:
            return etree.tostring(child)
    return None


#
# this is an exception to the usual pattern of 2-level-deep xml nodes
#
def find_xml_subnode(doc, anobject):
    if anobject.type == 'objects':
        node_names = anobject.el_name.split(':')
        print('>>> node_names[0] = %s, node_names[1] = %s' % (node_names[0], node_names[1]))
        print('>>> subtype=' + anobject.el_subtype)
        children = doc.findall(SF_NAMESPACE + anobject.el_type)
        print('>>> looking for ' + anobject.el_type)
        for child in children:
            node = child.find(SF_NAMESPACE + 'fullName')
            if node is not None:
                if node.text == node_names[0]:
                    if anobject.el_subtype == 'picklists':
                        plvalues = child.findall(SF_NAMESPACE + 'picklistValues')
                        for plvalue in plvalues:
                            if plvalue.find(SF_NAMESPACE + 'picklist').text == node_names[1]:
                                #
                                # due to difficulty we have to return everything from the root node
                                #
                                return etree.tostring(child)
    else:

        logging.getLogger('deploy').info('Unknown object type: ' + anobject.type)
    return None


def find_changes(filename, cache, objects):
    doc = etree.XML(cache[filename])
    buf = ''
    for anobject in objects:
        if anobject.status == 'd': return None
        print('looking for name=%s, type=%s' % (anobject.el_name, anobject.el_type))
        if anobject.el_name.find(':') >= 0:
            # recordType node
            xml = find_xml_subnode(doc, anobject)
        else:
            xml = find_xml_node(doc, anobject)

        if not xml:
            logging.getLogger('deploy').info("Did not find XML node for %s.%s.%s.%s" % (
                anobject.filename, anobject.el_type, anobject.el_name, anobject.el_subtype))
            return None
        buf += xml

    return buf


def get_meta_for_file(filename):
    with open(filename + '-meta.xml', 'r') as f:
        return f.read()


def has_duplicate(objectlist, obj):
    for o in objectlist:
        if o.el_name == obj.el_name and o.el_subtype == obj.el_subtype and o.filename == obj.filename:
            logger = logging.getLogger('deploy')
            logger.info('Rejected duplicate ' + obj.filename + '/' + obj.el_name)
            return True
    return False


def generate_package(object_list, output_name):
    global cache

    logger = logging.getLogger('deploy')

    default_ns = {None: 'http://soap.sforce.com/2006/04/metadata'}
    packagedoc = etree.Element('Package', nsmap=default_ns)
    etree.SubElement(packagedoc, 'version').text = "{0}".format(_API_VERSION)

    myzip = ZipFile(output_name, 'w', compression=ZIP_DEFLATED)

    logger.info('building %s', output_name)
    # create map and group by type
    object_map = {}
    for object in object_list:
        if object.type not in object_map:
            object_map[object.type] = []
        olist = object_map[object.type]
        if not has_duplicate(olist, object):
            olist.append(object)
    cache = create_file_cache(object_map)

    # objectPkgMap = {}   # holds all nodes to be added/updated, keyed by object/file name

    # labelchanges = ''
    for eltype, itemlist in object_map.items():
        if eltype not in typeMap:
            logger.error('** Unhandled type {0} - skipped'.format(eltype))
            continue

        logger.info('PROCESSING TYPE %s', eltype)

        if eltype == 'objects':
            register_object_changes(packagedoc, cache, itemlist, myzip)
        elif eltype == 'labels':
            register_label_changes(packagedoc, cache, itemlist, myzip)
        elif eltype in ['pages', 'classes', 'triggers']:
            register_code_changes(packagedoc, eltype, itemlist, cache, myzip)
        elif eltype == 'layouts':
            write_layout_definitions(packagedoc, eltype, itemlist, cache, myzip)
        elif eltype == 'email':
            register_email_changes(packagedoc, eltype, cache, itemlist, myzip)
        else:
            logger.warning('Type not supported: %s' % eltype)

            # if len(labelchanges) > 0:
            # writeLabelDefinitions(obj.filename, labelchanges, myzip)

    # writeObjectDefinitions(to_branch.repo, doc,  objectPkgMap, cache, myzip)

    xml = etree.tostring(packagedoc, xml_declaration=True, encoding='UTF-8', pretty_print=True)
    myzip.writestr('package.xml', xml)

    myzip.close()
    cache = {}
    return True


def register_email_changes(packagedoc, filetype, filecache, filelist, zipfile):
    names_for_package = []
    for member in filelist:
        print('member filename=%s, el_type=%s' % (member.filename, member.el_type))
        if member.filename.find('.') > 0:
            object_name = member.filename[0:member.filename.find('.')]
            names_for_package.append(object_name)
        if member.filename in filecache:
            zipfile.writestr(filetype + '/' + member.filename, filecache.get(member.filename))
            zipfile.writestr(filetype + '/' + member.filename + '-meta.xml',
                             get_meta_for_file(os.path.join('unpackaged', filetype, member.filename)))

    #
    # add entries to package.xml
    #
    el = etree.SubElement(packagedoc, 'types')
    for name in names_for_package:
        etree.SubElement(el, 'members').text = name
    etree.SubElement(el, 'name').text = typeMap[filetype]


def register_label_changes(packagedoc, filecache, members, zipfile):
    fragments = find_changes('CustomLabels.labels', filecache, [member for member in members if member.status != 'd'])
    write_label_definitions('CustomLabels.labels', fragments, zipfile)

    #
    # add only the requested labels to package.xml
    #
    el = etree.SubElement(packagedoc, 'types')
    etree.SubElement(el, 'name').text = typeMap['labels']
    for member in members:
        if member.status == 'd':
            continue
        etree.SubElement(el, 'members').text = member.el_name


def register_object_changes(packagedoc, cache, members, zipfile):
    logger = logging.getLogger('deploy')

    objectPkgMap = {}  # holds all nodes to be added/updated, keyed by object/file name

    packagedocs = {}

    #
    # build a map by object
    #
    for member in members:
        if member.status == 'd':
            continue
        if member.el_name is None:
            continue

        if member.filename not in objectPkgMap:
            objectPkgMap[member.filename] = []
        changes = objectPkgMap[member.filename]
        changes.append(member)

    #
    # Separate out the types into individual maps
    #
    for filename, items in objectPkgMap.items():
        packagedocs[filename] = cache[filename]

        types_el = etree.SubElement(packagedoc, 'types')
        etree.SubElement(types_el, 'name').text = typeMap['objects']
        etree.SubElement(types_el, 'members').text = filename[0:filename.find('.')]

    for filename, newdoc in packagedocs.items():
        write_object_definition(filename, newdoc, zipfile)


def slice_and_dice(packagedoc, maps, element_name):
    types_el = etree.SubElement(packagedoc, 'types')
    etree.SubElement(types_el, 'name').text = typeMap[element_name]
    for filename, items in maps.items():
        if len(items) == 0:
            # no elements of this type to deploy
            continue

        object_name = filename[0:filename.find('.')]
        #
        # add members to package.xml
        #
        for item in items:
            etree.SubElement(types_el, 'members').text = object_name + '.' + item.el_name

def register_change(doc, member, filetype):
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


def write_layout_definitions(packagedoc, filetype, filelist, filecache, zipfile):
    logger = logging.getLogger('deploy')
    for member in filelist:
        print('member filename=%s, el_type=%s' % (member.filename, member.el_type))
        if member.filename.find('.') > 0:
            object_name = member.filename[0:member.filename.find('.')]
        if os.path.isfile(os.path.join('unpackaged', filetype, member.filename)):
            zipfile.writestr(filetype + '/' + member.filename, filecache.get(member.filename))
            register_change(packagedoc, member, filetype)
            logger.info('storing: %s', member.filename)


def register_code_changes(packagedoc, filetype, filelist, filecache, zipfile):
    logger = logging.getLogger('deploy')
    names_for_package = []
    for member in filelist:
        print('member filename=%s, el_type=%s' % (member.filename, member.el_type))
        if member.filename.find('.') > 0:
            object_name = member.filename[0:member.filename.find('.')]
            names_for_package.append(object_name)
        ## !! assumes the right-side branch is still current in git !!
        if member.filename in filecache:
            zipfile.writestr(filetype + '/' + member.filename, filecache.get(member.filename))
            zipfile.writestr(filetype + '/' + member.filename + '-meta.xml',
                             get_meta_for_file(os.path.join('unpackaged', filetype, member.filename)))
            logger.info('storing: %s', member.filename)

    #
    # add entries to package.xml
    #
    el = etree.SubElement(packagedoc, 'types')
    for name in names_for_package:
        etree.SubElement(el, 'members').text = name
    etree.SubElement(el, 'name').text = typeMap[filetype]


def write_label_definitions(filename, element, zipfile):
    xml = '<?xml version="1.0" encoding="UTF-8"?>' \
          '<CustomLabels xmlns="http://soap.sforce.com/2006/04/metadata">'
    xml += element
    xml += '</CustomLabels>'
    zipfile.writestr('labels/' + filename, xml)


def write_object_definition(filename, doc, zipfile):
    xml = etree.tostring(doc, xml_declaration=True, encoding='UTF-8', pretty_print=True)
    zipfile.writestr('objects/' + filename, xml)


def resetLocalRepo(branch_name):
    subprocess.check_call(["git", "checkout", branch_name])


#    subprocess.check_call(["git","reset","--hard","{0}".format(branch_name)])

def build_package_file(release_id, objectList, from_branch, packagedir='/var/sftmp'):
    if packagedir == None:
        packagedir = '/var/sftmp'
    os.chdir(from_branch.repo.location)
    resetLocalRepo(from_branch.name)
    output_name = os.path.join(packagedir, f'deploy_{from_branch.name}_{release_id}.zip')
    r = generate_package(objectList, output_name)
    if r:
        return output_name
    else:
        os.unlink(output_name)
        return None

# needs work
def deploy(filename, to_branch, testOnly = True, retain_package=False):
    agent = Utils.getAgentForBranch(to_branch, logger=logging.getLogger('deploy'))
    results = agent.deploy(filename, testOnly)
    if not retain_package:
        os.unlink(filename)
    return results

#
# External entry point
#

def make_package(deployPkg) -> (bool, str):

    package_name = build_package_file(deployPkg.release.id, deployPkg.deployable_objects.all(),
                     deployPkg.source_environment)
    if package_name is None:
        deployPkg.package_location = None
        deployPkg.save()
        return False, 'Package build failed'

    deployPkg.package_location = package_name
    deployPkg.save()
    return True, None


#needs work
def deploy_package(pkgStatus):
    deployPkg = pkgStatus.package
    to_branch = pkgStatus.target_environment

    results = deploy(deployPkg.deployable_objects.all(),
                     deployPkg.source_environment,
                     to_branch,
                     testOnly=pkgStatus.test_only,
                     retain_package=pkgStatus.keep_package,
                     packagedir=pkgStatus.package_location)
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
