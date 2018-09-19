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
import json
import os
from datetime import date
from datetime import datetime
from datetime import timedelta

import sys
from django.utils.encoding import smart_str
from django.shortcuts import redirect, render
from django.http import HttpResponse

from stratosource.management.Utils import doGrep
from stratosource.models import DeploymentPushStatus, DeploymentPackage, Story, Release, DeployableObject, \
    DeployableTranslation, Delta, Branch, ConfigSetting, SalesforceUser, Repo, BranchStats, UnitTestBatch
from stratosource.user import rallyintegration
from stratosource.user import agilezenintegration
from stratosource.management import ConfigCache, Deployment, labels
import logging

logger = logging.getLogger('console')
namestl = {
    'homePageComponents': 'Homepage Components',
    'homePageLayouts': 'Homepage Layouts',
    'objectTranslations': 'Object Translations',
    'reportTypes': 'Report Types',
    'remoteSiteSettings': 'Remote Site Settings',
    'staticresources': 'Static Resources',
    'scontrols': 'S-Controls',
    'weblinks': 'Web Links'
}


def configs(request):
    allsettings = ConfigSetting.objects.all();

    if request.method == u'POST':
        params = dict(request.POST.items())
        for param in params:
            if param.startswith('key_'):
                key = smart_str(param, 'utf-8', False)[4:]
                value = request.POST[param]
                for setting in allsettings:
                    if key == setting.key:
                        if setting.value != value:
                            if setting.masked:
                                # only proceed with update if masked value is not empty
                                if value != '':
                                    repValue = request.POST[param + '_2']
                                    logger.debug('Checking if the values match!')
                                    if repValue == value:
                                        logger.debug('Values Match!')
                                        setting.value = value
                                        setting.save()
                            else:
                                setting.value = value
                                setting.save()

        # Handle checkboxes
        for setting in allsettings:
            if setting.type == 'check':
                if not request.POST.__contains__('key_' + setting.key):
                    setting.value = '0'
                    setting.save()

        ConfigCache.refresh()
        allsettings = ConfigSetting.objects.all()
        return render(request, 'home.html')

    data = {'settings': allsettings.order_by('key')}
    for setting in allsettings:
        if setting.type == 'check':
            data[setting.key.replace('.', '_')] = setting.value == '1'
        else:
            data[setting.key.replace('.', '_')] = setting.value

    return render(request, 'configs.html', data)


def verify_configuration():
    from django.db import connections
    import os
    conn = connections['default']
    try:
        c = conn.cursor()
        # test that a few tables exist
        c.execute('select * from branch limit 1')
        c.execute('select * from story limit 1')
        c.execute('select * from delta limit 1')
        if not os.path.isdir('/var/sfrepo'):
            return False
    except Exception:
        return False
    return True


def home(request):
    #    if not verify_configuration():
    #        return render(request,'setup.html', {'stage': '10'})

    branches = Branch.objects.filter(enabled=True).order_by('order')
    bstats = BranchStats.objects.filter(branch__enabled=True).order_by('branch__order')
    try:
        utrecent = UnitTestBatch.objects.filter(branch__enabled=True).latest('batch_time')
    except Exception:
        utrecent = None

    data = {'branches': branches, 'stats': bstats, 'unittest': utrecent}

    # data['calendar_host'] = ConfigCache.get_config_value('calendar.host')
    # if data['calendar_host'] == 'localhost':
    #    data['calendar_host'] = request.get_host().split(':')[0]

    return render(request, 'home.html', data)


def create_release_package(request):
    release_id = None
    branch_id = None
    branches = Branch.objects.filter(enabled__exact=True).order_by('order')

    if request.method == u'POST':
        release_id = request.POST.get('releaseId')
        release = Release.objects.get(id=release_id)
        release_package = DeploymentPackage()
        release_package.release = release
        release_package.name = request.POST.get('txtName')
        release_package.source_environment = Branch.objects.get(id=request.POST.get('sourceBranchId'))
        release_package.save()
        ids = request.POST.getlist('objId')
        objects = DeployableObject.objects.filter(id__in=ids)
        for o in objects.all():
            if o not in release_package.deployable_objects.all():
                release_package.deployable_objects.add(o)
        release_package.save()
        return redirect('/release/' + str(release_package.release.id))

    if request.method == u'GET':
        release_id = request.GET.get('release_id')
        branch_id = request.GET.get('branch_id')
        release = Release.objects.get(id=release_id)
        from_branch = Branch.objects.get(id=branch_id)

        manifest = []
        for story in release.stories.all():
            deployables = DeployableObject.objects.filter(pending_stories=story, branch=from_branch)
            dep_objects = DeployableObject.objects.filter(released_stories=story, branch=from_branch)
            deployables.select_related()
            dep_objects.select_related()
            manifest += list(deployables)
            manifest += list(dep_objects)

            manifest.sort(key=lambda object: object.type + object.filename)

            data = {'release': release, 'manifest': manifest, 'branches': branches, 'from_branch': from_branch}

    return render(request, 'release_create_package.html', data)


def deployment_dashboard(request):
    packages = DeploymentPackage.objects.all().order_by('-date_added')
    attempts = DeploymentPushStatus.objects.all().order_by('-date_attempted')

    return render(request, 'deployment.html', {'packages': packages, 'attempts': attempts})


def release_package(request, release_package_id):
    release_package = DeploymentPackage.objects.get(id=release_package_id)

    release_attempts = DeploymentPushStatus.objects.filter(package=release_package)

    data = {'release_package': release_package, 'release_attempts': release_attempts}
    return render(request, 'release_package.html', data)


def delete_release_package(request, release_package_id):
    release_package = DeploymentPackage.objects.get(id=release_package_id)
    release_id = release_package.release.id
    release_package.delete()
    return redirect('/release/' + str(release_id))


def push_release_package(request, release_package_id):
    release_package = DeploymentPackage.objects.get(id=release_package_id)

    if request.method == u'POST':
        branch = Branch.objects.get(id=request.POST.get('target_env'))

        push_package = DeploymentPushStatus()
        push_package.package = release_package
        push_package.keep_package = request.POST.get('keep_generated') == '1'
        push_package.package_location = '/tmp'
        push_package.test_only = False
        push_package.target_environment = branch
        push_package.save()

        if os.fork() == 0:
            Deployment.deploy_package(push_package)
            sys.exit()

        return redirect('/release_push_status/' + str(push_package.id))

    branches = Branch.objects.filter(enabled__exact=True).order_by('order')
    data = {'release_package': release_package, 'branches': branches}

    return render(request, 'release_push_package.html', data)


def release_push_status(request, release_package_push_id):
    push_package = DeploymentPushStatus.objects.get(id=release_package_push_id)
    data = {'push_package': push_package}

    return render(request, 'release_push_status.html', data)


# def export_labels(request, release_id, selectionError=False):
#    data = {'repos': Repo.objects.all()}
#    data['release'] = Release.objects.get(id=release_id)
#    data['release_id'] = release_id
#    d#ata['repoSelectionError'] = selectionError
#    return render(request,'export_labels_form.html', data)


def export_labels_form(request):
    release_id = request.GET.get('release_id')
    branch_id = request.GET.get('branch_id')
    if branch_id is None or len(branch_id) == 0:
        return release(request, release_id)

    branch = Branch.objects.get(id=branch_id)
    ssfile = labels.generateLabelSpreadsheet(branch, release_id)
    response = HttpResponse(ssfile, content_type='application/xls')
    response['Content-Disposition'] = 'attachment; filename="%s_labels.xls"' % branch.name
    return response


def manifest(request, release_id):
    release = Release.objects.get(id=release_id)
    release.release_notes = release.release_notes.replace('\n', '<br/>')
    manifest = []
    branch = Branch()

    if request.GET.__contains__('branch'):
        release_story_id_list = set([story.rally_id for story in release.stories.all()])

        branch = Branch.objects.get(id=request.GET.get('branch'))
        for story in release.stories.all():
            deployables = DeployableObject.objects.filter(pending_stories=story, branch=branch)
            dep_objects = DeployableObject.objects.filter(released_stories=story, branch=branch)
            deployables.select_related()
            dep_objects.select_related()
            manifest += list(deployables)
            manifest += list(dep_objects)

    for deployable in manifest:
        #
        # it is necessary to copy pending_stories.all() to a non-django array to
        # preserve custom data we are attaching to pass to the UI
        #
        deployable.stories = []
        for story in deployable.pending_stories.all():
            deployable.stories.append(story)
            if not story.rally_id in release_story_id_list:
                story.status = 'warning'
            else:
                story.status = 'confirmed'

    manifest.sort(key=lambda object: object.type + object.filename)
    branches = Branch.objects.filter(enabled__exact=True).order_by('order')

    data = {'release': release, 'manifest': manifest, 'branches': branches, 'branch': branch}
    return render(request, 'release_manifest.html', data)


def search(request):
    repos = Repo.objects.all()
    searchtext = ''
    selectedrepo = ''
    selectedbranch = ''
    if request.GET.__contains__('searchText'): searchtext = request.GET['searchText']
    if request.GET.__contains__('selectedRepo'): selectedrepo = request.GET['selectedRepo']
    if request.GET.__contains__('selectedBranch'): selectedbranch = request.GET['selectedBranch']

    if request.GET.__contains__('selectedRepo'):
        repo = Repo.objects.get(name__exact=selectedrepo)
        branches = Branch.objects.filter(repo=repo, enabled__exact=True).order_by('order')
    else:
        branches = []
    results = []
    if request.GET.__contains__('go'):
        repo = Repo.objects.get(name__exact=selectedrepo)
        # branch = Branch.objects.get(repo=repo, name__exact=selectedBranch)
        results = {}
        results['classes'] = doGrep(repo.location + '/unpackaged/classes', 'cls', searchtext)
        results['triggers'] = doGrep(repo.location + '/unpackaged/triggers', 'trigger', searchtext)
        results['pages'] = doGrep(repo.location + '/unpackaged/pages', 'page', searchtext)

    data = {'results': results, 'repos': repos, 'branches': branches, 'searchText': searchtext,
            'selectedRepo': selectedrepo, 'selectedBranch': selectedbranch}
    return render(request, 'search.html', data)


def releases(request):
    unreleased = Release.objects.filter(released__exact=False)

    data = {'unreleased_list': unreleased, 'branches': Branch.objects.filter(enabled__exact=True).order_by('order')}
    return render(request, 'releases.html', data)


def release(request, release_id):
    release = Release.objects.get(id=release_id)
    branches = Branch.objects.filter(enabled__exact=True).order_by('order')
    deployment_packages = DeploymentPackage.objects.filter(release=release)

    if request.method == u'GET' and request.GET.__contains__('remove_story_id'):
        story = Story.objects.get(id=request.GET['remove_story_id'])
        release.stories.remove(story)
        release.save()

    if request.method == u'POST' and request.POST.__contains__('releaseNotes'):
        release.release_notes = request.POST['releaseNotes']
        release.save()

    data = {'release': release, 'avail_stories': stories, 'branches': branches,
            'deployment_packages': deployment_packages}
    return render(request, 'release.html', data)


def unreleased(request, repo_name, branch_name):
    branch = Branch.objects.get(repo__name=repo_name, name=branch_name)

    if request.method == u'GET' and request.GET.__contains__('releaseAll') and request.GET['releaseAll'] == 'true':
        deltas = Delta.objects.exclude(object__release_status='r').filter(object__branch=branch)
        deltas.select_related()
        for delta in deltas.all():
            delta.object.release_status = 'r'
            delta.object.save()

    go = ''
    search = ''
    username = ''
    typeFilter = ''
    endDate = date.today()
    startDate = endDate + timedelta(days=-14)
    objectTypesData = DeployableObject.objects.values('type').order_by('type').distinct()
    objectTypes = list()
    for type in objectTypesData:
        if type['type'] != '':
            objectTypes.append(type['type'])

    if request.method == u'GET':
        if request.GET.__contains__('go'):
            go = 'true'
        if request.GET.__contains__('search'):
            search = request.GET['search']
        if request.GET.__contains__('username'):
            username = request.GET['username']
        if request.GET.__contains__('startDate'):
            startDate = datetime.strptime(request.GET['startDate'], "%m/%d/%Y")
        if request.GET.__contains__('endDate'):
            endDate = datetime.strptime(request.GET['endDate'], "%m/%d/%Y")
        if request.GET.__contains__('type'):
            typeFilter = request.GET['type']

    uiEndDate = endDate
    endDate = endDate + timedelta(days=1)

    deltas = []
    objects = []
    deltaMap = {}
    user = ''
    changeDate = ''

    if request.GET.__contains__('go'):
        deltas = Delta.objects.filter(object__branch=branch).filter(commit__date_added__gte=startDate).filter(
            commit__date_added__lte=endDate)

        if len(username) > 0:
            deltas = deltas.filter(user_change__sfuser__name=username)

        if len(search) > 0:
            deltas = deltas.extra(where=[
                '(filename LIKE \'%%' + search + '%%\' or type LIKE \'%%' + search + '%%\' or el_type LIKE \'%%' + search + '%%\' or el_subtype LIKE \'%%' + search + '%%\' or el_name LIKE \'%%' + search + '%%\')'])

        if len(typeFilter) > 0:
            deltas = deltas.extra(where=['type = \'' + typeFilter + '\''])

        deltas = deltas.order_by('object__type', 'object__filename', 'object__el_type', 'object__el_subtype',
                                 'object__el_name', 'commit__date_added')

        logger.debug('Deltas SQL ' + str(deltas.query))
        deltas.select_related()

        for delta in deltas.all():
            changelog = deltaMap.get(delta.object)
            if delta.user_change and delta.user_change.sfuser.name != '':
                user = ' by ' + delta.user_change.sfuser.name
                changeDate = ' at ' + str(delta.user_change.last_update)[:16]
            else:
                user = ''
                changeDate = ''

            if changelog:
                if not changelog.endswith(delta.getDeltaType() + user + changeDate):
                    changelog += '\n' + delta.getDeltaType() + user + changeDate

                deltaMap[delta.object] = changelog
            else:
                objects.append(delta.object)
                deltaMap[delta.object] = delta.getDeltaType() + user + changeDate

    userList = SalesforceUser.objects.values('name').order_by('name').distinct()
    users = [u['name'] for u in userList]

    annotations = []
    if ConfigCache.get_config_value('show.todo') == '1':
        todofile = os.path.join(branch.repo.location, '..', 'annotations_' + branch.name + '.txt')
        try:
            if os.path.exists(todofile):
                with open(todofile, 'r') as f:
                    annotations = json.loads(f.read())['annotations']
        except:
            pass

    data = {
        'branch_name': branch_name,
        'repo_name': branch.repo.name,
        'objects': objects,
        'startDate': startDate,
        'endDate': uiEndDate,
        'deltaMap': deltaMap,
        'namestl': namestl,
        'users': users,
        'search': search,
        'username': username,
        'go': go,
        'objectTypes': objectTypes,
        'selectedType': typeFilter,
        'todos': annotations
    }
    return render(request, 'unreleased.html', data)


def object(request, object_id):
    object = DeployableObject.objects.get(id=object_id)
    deltas = Delta.objects.filter(object__filename=object.filename, object__branch__id=object.branch.id).order_by(
        'commit__branch__name', '-commit__date_added')
    data = {'object': object, 'deltas': deltas}
    return render(request, 'object.html', data)


def stories(request):
    if request.method == u'POST' and request.POST.__contains__('releaseid'):
        release = Release.objects.get(id=request.POST['releaseid'])
        if request.POST.__contains__('storyId'):
            ids = request.POST.getlist('storyId')
            sprint_name = request.POST['cboSprints']

            print('sprint_name ' + sprint_name)

            if sprint_name != '':
                for story in release.stories.all():
                    if story.sprint == sprint_name:
                        print('removing ' + story.name)
                        release.stories.remove(story)
            else:
                release.stories.clear()

            stories = Story.objects.filter(id__in=ids)
            for s in stories.all():
                if s not in release.stories.all():
                    # this print was causing a unicode issue adding a story, so commented out
                    # print 'adding ' + s.name
                    release.stories.add(s)
        release.save()
        return redirect('/release/' + str(release.id))

    if request.method == u'GET' and request.GET.__contains__('delete'):
        story = Story.objects.get(id=request.GET['delete'])
        objects = DeployableObject.objects.filter(pending_stories=story)
        for object in objects:
            object.pending_stories.remove(story)
            object.save()
        story.delete()

    if request.method == u'GET' and request.GET.__contains__('refresh'):
        if ConfigCache.get_config_value('agilezen.enabled') == '1':
            agilezenintegration.refresh()
        if ConfigCache.get_config_value('rally.enabled') == '1':
            rallyintegration.refresh()

    releaseid = ''
    in_release = {}
    if request.method == u'GET' and request.GET.__contains__('releaseid'):
        releaseid = request.GET['releaseid']
        if len(releaseid) > 0:
            release = Release.objects.get(id=request.GET['releaseid'])
            for story in release.stories.all():
                in_release[story.id] = True

    sprint = ''
    if request.method == u'GET' and request.GET.__contains__('sprint'):
        sprint = request.GET['sprint']

    sprintList = []
    oneYear = timedelta(days=365)
    oneYearAgo = datetime.now() - oneYear

    if request.method == u'GET' and request.GET.__contains__('history'):
        sprints = Story.objects.values('sprint').filter(sprint__isnull=False).order_by('sprint').distinct()
    else:
        sprints = Story.objects.values('sprint').filter(sprint__isnull=False, date_added__gte=oneYearAgo).order_by(
            'sprint').distinct()

    for sprintName in sprints:
        if len(sprintName['sprint']) > 0 and not sprintList.__contains__(sprintName['sprint']):
            sprintList.append(sprintName['sprint'])

    if request.method == u'GET' and request.GET.__contains__('history'):
        stories = Story.objects.all()
    else:
        stories = Story.objects.filter(date_added__gte=oneYearAgo)

    if len(sprint) > 0:
        stories = stories.filter(sprint=sprint)
    stories = stories.order_by('sprint', 'rally_id', 'name')
    # Need to cast the rally_id to prevent duplicate stories from coming over
    # different SQL needed for mySQL and SQLite
    ## MySQL compatible call
    if ConfigCache.get_config_value('agilezen.enabled') == '1':
        stories = stories.extra(select={'rally_id': 'CAST(rally_id AS SIGNED)'}).extra(order_by=['rally_id'])
        ## SQLite compatible call
        # stories = stories.extra(select={'rally_id': 'CAST(rally_id AS INTEGER)'}).extra(order_by = ['rally_id'])
    stories.select_related()
    stories_refresh_enabled = (ConfigCache.get_config_value('rally.enabled') == '1') or (
            ConfigCache.get_config_value('agilezen.enabled') == '1')
    data = {'stories': stories, 'rally_refresh': stories_refresh_enabled, 'releaseid': releaseid,
            'in_release': in_release, 'sprintList': sprintList, 'sprint': sprint}

    return render(request, 'stories.html', data)


def instory(request, story_id):
    story = Story.objects.get(id=story_id)
    branches = []
    dep_branches = []
    all_branches = Branch.objects.filter(enabled__exact=True).order_by('order')

    if request.method == u'GET' and request.GET.__contains__('remove'):
        obj = DeployableObject.objects.get(id=request.GET['assoc'])
        obj.pending_stories.remove(story)
        obj.save()

    if request.method == u'GET' and request.GET.__contains__('release'):
        branch = Branch.objects.get(name=request.GET['release'])
        story.done_on_branches.add(branch)
        objects = DeployableObject.objects.filter(pending_stories=story, branch=branch)
        for object in objects:
            object.pending_stories.remove(story)
            object.released_stories.add(story)
            if (len(object.pending_stories.all()) == 0):
                object.release_status = 'r';
            object.save()
        translations = DeployableTranslation.objects.filter(pending_stories=story, branch=branch)
        for trans in translations:
            trans.pending_stories.remove(story)
            trans.released_stories.add(story)
            if (len(trans.pending_stories.all()) == 0):
                trans.release_status = 'r';
            trans.save()
        story.save()

    objects = DeployableObject.objects.filter(pending_stories=story).order_by('branch__name', 'type', 'filename',
                                                                              'el_type', 'el_subtype', 'el_name')
    objects.select_related()

    translations = DeployableTranslation.objects.filter(pending_stories=story).order_by('branch__name', 'label',
                                                                                        'locale')
    translations.select_related()

    for obj in objects:
        if obj.branch not in branches:
            branches.append(obj.branch)
    for trans in translations:
        if trans.branch not in branches:
            branches.append(trans.branch)

    dep_objects = DeployableObject.objects.filter(released_stories=story).order_by('branch__name', 'type', 'filename',
                                                                                   'el_type', 'el_subtype', 'el_name')
    dep_objects.select_related()

    dep_translations = DeployableTranslation.objects.filter(released_stories=story).order_by('branch__name', 'label',
                                                                                             'locale')
    dep_translations.select_related()

    for obj in dep_objects:
        if obj.branch not in dep_branches:
            dep_branches.append(obj.branch)
    for trans in dep_translations:
        if trans.branch not in dep_branches:
            dep_branches.append(trans.branch)

    releases = Release.objects.filter(released=False, stories__id=story.id)

    data = {'story': story, 'objects': objects, 'dep_objects': dep_objects, 'translations': translations,
            'dep_translations': dep_translations, 'branches': branches, 'dep_branches': dep_branches,
            'all_branches': all_branches, 'releases': releases}
    if request.method == u'GET' and request.GET.__contains__('branch_name') and request.GET.__contains__('repo_name'):
        data['branch_name'] = request.GET['branch_name']
        data['repo_name'] = request.GET['repo_name']

    return render(request, 'in_story.html', data)


def rally_projects(request):
    if request.method == u'GET' and request.GET.__contains__('chkProject'):
        pickedProjs = request.GET.getlist('chkProject')
        isFirst = True
        projectConfValue = ''
        for p in pickedProjs:
            if not isFirst:
                projectConfValue = projectConfValue + ';'
            isFirst = False
            projectConfValue = projectConfValue + p

        ConfigCache.store_config_value('rally.pickedprojects', projectConfValue)
        return redirect('/configs/')

    projects = []
    if ConfigCache.get_config_value('rally.enabled') == '1':
        projlist = rallyintegration.get_projects(True)
        for project in projlist:
            projects.append(project)

    if ConfigCache.get_config_value('agilezen.enabled') == '1':
        projlist = agilezenintegration.get_projects(True)
        for project in projlist:
            projects.append(project)

    data = {'projects': projects}
    return render(request, 'rally_projects.html', data)
