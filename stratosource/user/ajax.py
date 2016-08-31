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
from datetime import datetime, timedelta

from django.utils import timezone

from stratosource.models import Release, Story, Branch, DeployableObject, DeployableTranslation, ReleaseTask, SalesforceUser
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse
from django.shortcuts import render_to_response
import json
from django.db import transaction
from django.db.models import Q
#from stratosource.user import calendar
import logging
import traceback

logger = logging.getLogger('console')

def createrelease(request):
    results = {'success':False}
    
    if request.method == u'GET':
        try:
            release = Release()
            release.name = request.GET['name']
            reldate = datetime.strptime(request.GET['estRelDate'] + 'T09:09:09', '%b. %d, %YT%H:%M:%S')
            release.est_release_date = reldate
            release.save()
            results = {'success':True}

#            calendar.addCalendarReleaseEvent(release.id, release.name, reldate)

        except Exception as ex:
            results = {'success':False, 'error':ex}


    js = json.dumps(results)
    return HttpResponse(js, content_type='application/json')

def updaterelease(request):
    results = {'success':False}

    if request.method == u'GET':
        try:
            release = Release.objects.get(id=request.GET['id'])
            date = ''
            name = ''
            reldate = None
            try:
                reldate = datetime.strptime(request.GET['date'] + 'T09:09:09', '%b. %d, %YT%H:%M:%S')
            except Exception as ex:
                reldate = datetime.strptime(request.GET['date'] + 'T09:09:09', '%B %d, %YT%H:%M:%S')
                
            release.est_release_date = reldate
            name = request.GET['name']
            release.name = name

#            calendar.updateCalendarReleaseEvent(release.id, release.name, reldate)

            release.save()
            results = {'success':True}
            

        except Exception as ex:
            results = {'success':False, 'error':ex}

    js = json.dumps(results)
    return HttpResponse(js, content_type='application/json')

def deleterelease(request):
    results = {'success':False}

    if request.method == u'GET':
        try:
#            calendar.removeCalendarReleaseEvent(request.GET['id'])

            release = Release.objects.get(id=request.GET['id'])
            release.delete()
            results = {'success':True}
        except Exception as ex:
            results = {'success':False, 'error':ex}

    js = json.dumps(results)
    return HttpResponse(js, content_type='application/json')

def markreleased(request):
    results = {'success':False}

    if request.method == u'GET':
        try:
            release = Release.objects.get(id=request.GET['id'])
            release.released = True
            release.release_date = datetime.now()
            release.save()
            for story in release.stories.all():
#                story.done_on_branches.add(release.branch)
                objects = DeployableObject.objects.filter(pending_stories=story)
                for object in objects:
                    object.pending_stories.remove(story)
                    object.released_stories.add(story)

                    non_releasing_stories = set()
                    for story in object.pending_stories.all():
                        if story not in release.stories.all():
                            non_releasing_stories.add(story)
                    
                    if (len(non_releasing_stories) == 0):
                        object.release_status = 'r';
                    object.save()
                translations = DeployableTranslation.objects.filter(pending_stories=story)
                for trans in translations:
                    trans.pending_stories.remove(story)
                    trans.released_stories.add(story)

                    non_releasing_stories = set()
                    for story in trans.pending_stories.all():
                        if story not in release.stories.all():
                            non_releasing_stories.add(story)
                    
                    if (len(non_releasing_stories) == 0):
                        trans.release_status = 'r';
                    trans.save()
            results = {'success':True}
        except Exception as ex:
            results = {'success':False, 'error':ex.message}

    js = json.dumps(results)
    return HttpResponse(js, content_type='application/json')

def releases(request):
    if request.method == u'GET':
        releases = Release.objects.filter(hidden=False).order_by('released', 'est_release_date', 'release_date', 'name')
        data = {'releases': releases}

        return render_to_response('ajax_releases.html', data )

def ignoreitem(request, object_id):
    results = {'success':False}
    ok = request.GET['ok']
    try:
        object = DeployableObject.objects.get(id=object_id)
        if ok == 'true':
            if len(object.pending_stories.all()) > 0:
                object.release_status = 'p'
            else:
                object.release_status = 'c'
            object.save()
            results = {'success':True}
        else:
            if len(object.pending_stories.all()) == 0:
                object.release_status = 'r'
                object.save()
                results = {'success':True}
            else:
                results = {'success': False, 'error': 'Object is assigned to a story'}
    except Exception as ex:
        results = {'success':False, 'error':ex}

    js = json.dumps(results)
    return HttpResponse(js, content_type='application/json')

def ignoretranslation(request, trans_id):
    results = {'success':False}
    ok = request.GET['ok']
    try:
        trans = DeployableTranslation.objects.get(id=trans_id)
        if ok == 'true':
            if len(trans.pending_stories.all()) > 0:
                trans.release_status = 'p'
            else:
                trans.release_status = 'c'
            trans.save()
            results = {'success':True}
        else:
            if len(trans.pending_stories.all()) == 0:
                trans.release_status = 'r'
                trans.save()
                results = {'success':True}
            else:
                results = {'success': False, 'error': 'At least one object is assigned to a story'}
    except Exception as ex:
        results = {'success':False, 'error':ex}

    js = json.dumps(results)
    return HttpResponse(js, content_type='application/json')

@transaction.atomic
def ignoreselected(request):
    results = {'success':False}

    try:
        objectIds = request.GET.getlist('ii');

        objects = DeployableObject.objects.filter(id__in=objectIds)
        for object in objects:
            if len(object.pending_stories.all()) == 0:
                object.release_status = 'r'
                object.save()

        transIds = request.GET.getlist('ti');

        translations = DeployableTranslation.objects.filter(id__in=transIds)
        for translation in translations:
            if len(translation.pending_stories.all()) == 0:
                translation.release_status = 'r'
                translation.save()

        results = {'success':True}

    except Exception as ex:
        results = {'success':False, 'error':ex}

    js = json.dumps(results)
    return HttpResponse(js, content_type='application/json')

def getstories(request):
    results = {'success':False}
    try:
        storyList = ['None|']
        stories = []
        sprint = 'All'
        if request.GET.__contains__('sprintName'):
            sprint = request.GET['sprintName'];
        if sprint != 'None':
            if len(sprint) > 0 and sprint != 'All':
                stories = Story.objects.filter(sprint=sprint).order_by('rally_id', 'name')
            else:
                stories = Story.objects.all().order_by('rally_id', 'name')
    
            for story in stories:
                if len(story.rally_id) > 0:
                    name = story.rally_id + ': '
    
                storyList.append(name + story.name + '|' + str(story.id))
        results = {'success':True, 'stories': storyList, 'numStories': len(stories)}
    except Exception as ex:
        results = {'success':False, 'error':ex.message}

    jso= json.dumps(results)
    return HttpResponse(jso, content_type='application/json')

def getsprints(request):
    results = {'success':False}
    try:
        threeMonths = timedelta(days = 90)
        threeMonthsAgo = timezone.now() - threeMonths
        sprintList = ['None','All']
        stories = Story.objects.values('sprint').filter(sprint__isnull=False, date_added__gte=threeMonthsAgo).order_by('sprint').distinct()

        for story in stories:
            if len(story['sprint']) > 0 and not sprintList.__contains__(story['sprint']):
                sprintList.append(story['sprint'])
        
        results = {'success':True, 'sprints': sprintList, 'numSprints': len(sprintList)}
    except Exception as ex:
        results = {'success':False, 'error':ex.message}

    js = json.dumps(results)
    return HttpResponse(js, content_type='application/json')


def addtostory(request):

    log = logging.getLogger('user')

    results = {'success':False}

    if request.method == u'GET':
        story = None
        try:
            storyId = request.GET['storyId']
            if (storyId == 'null'):
                storyId = ''
            storyName = request.GET['storyName']
            storyRallyId = request.GET['storyRallyId']
            storyURL = request.GET['storyURL']

            if len(storyId) > 0 or len(storyRallyId) > 0:

                if len(storyId) > 0:
                    try:
                        story = Story.objects.get(id=storyId)
                    except ObjectDoesNotExist:
                        pass

                if not story and len(storyRallyId) > 0:
                    try:
                        story = Story.objects.get(rally_id=storyRallyId)
                    except ObjectDoesNotExist:
                        pass

                if not story:
                    story = Story()
                    if len(storyRallyId) > 0:
                        story.rally_id = storyRallyId
                        story.url = "https://rally1.rallydev.com/slm/detail/" + story.rally_id
                    if len(storyURL) > 0:
                        story.url = storyURL

                if len(storyName) > 0:
                    story.name = storyName
                    
                story.save()
                
            objectIds = request.GET.getlist('itemid');

            objects = DeployableObject.objects.filter(id__in=objectIds)
            for object in objects:
                if story:
                    object.pending_stories.add(story)
                    object.release_status = 'p'
                object.save()

            transIds = request.GET.getlist('transid');

            translations = DeployableTranslation.objects.filter(id__in=transIds)
            for translation in translations:
                if story:
                    translation.pending_stories.add(story)
                    translation.release_status = 'p'
                translation.save()

            results = {'success':True}
        except Exception as ex:
            tb = traceback.format_exc()
            results = {'success':False, 'error':'ERROR: ' + tb}

    js = json.dumps(results)
    return HttpResponse(js, content_type='application/json')

def get_release_tasks(request, type, id):
    if type == 'r':
        release = Release.objects.get(id=id)
        tasks = ReleaseTask.objects.filter(Q(release=release) | Q(story__in=release.stories.all())).order_by('task_type','order')
    else:
        story = Story.objects.get(id=id)
        tasks = ReleaseTask.objects.filter(story=story).order_by('task_type','order')
    
    branches = Branch.objects.filter(enabled__exact = True).order_by('order')
    users = SalesforceUser.objects.all().order_by('name')

    
    for task in tasks:
        task.done_in_branch_list = task.done_in_branch.split(',')
        for ttype in task.TASK_TYPES:
            if ttype[0] == task.task_type:
                task.task_type_name = ttype[1]
        
    for branch in branches:
        branch.tid = str(branch.id)
    
    data = {'success':True, 'tasks': tasks, 'branches': branches, 'readonly' : request.GET.__contains__('readonly'), 'users' : users, 'type': type}

    return render_to_response('release_tasks_ajax.html', data)
    
def add_release_task(request):
    results = {'success':False}
    try:
        task = ReleaseTask()
        if request.GET.__contains__('rel_id') and request.GET['rel_id'] != 'null':
            release = Release.objects.get(id=request.GET['rel_id'])
            task.release = release
        if request.GET.__contains__('story_id') and request.GET['story_id'] != 'null':
            story = Story.objects.get(id=request.GET['story_id'])
            task.story = story
            
        task.order = 999
        task.name = request.GET['task']
        task.save()
        
        results = {'success':True}
    except Exception as ex:
        results = {'success':False, 'error':ex.message}

    js = json.dumps(results)
    return HttpResponse(js, content_type='application/json')
    
def edit_release_task(request):
    task_id = request.GET['task_id']
    
    done_on_branch = request.GET['branch_id']
    
    task = ReleaseTask.objects.get(id=task_id)
    
    if request.GET.__contains__('newVal'):
        newVal = request.GET['newVal']
        task.name = newVal

    if request.GET.__contains__('user_id'):
        user_id = request.GET['user_id']
        task.user = SalesforceUser.objects.get(id=user_id)

    if request.GET.__contains__('type_id'):
        task_type = request.GET['type_id']
        task.task_type = task_type
        
    if request.GET.__contains__('done'):
        is_done = request.GET['done'] == 'true'
        task.done_in_branch_list = task.done_in_branch.split(',')
        try:
            task.done_in_branch_list.remove(done_on_branch)
        except Exception:
            logger.debug('Not in list')
    
        if is_done:
            task.done_in_branch_list.append(done_on_branch)
    
        str = ''
        for id in task.done_in_branch_list:
            if id != '':
                if str == '':
                    str = id
                else:
                    str = str + ',' + id
    
        task.done_in_branch = str
        logger.debug('task.done_in_branch ' + task.done_in_branch)
    
    task.save()

    results = {'success':True}

    js = json.dumps(results)
    return HttpResponse(js, content_type='application/json')    

@transaction.atomic
def reorder_release_tasks(request):
    order = request.GET['order']
    id_list = order.split(',')
    i = 0
    for id in id_list:
        task = ReleaseTask.objects.get(id=id)
        task.order = i
        i = i + 1
        task.save()

    results = {'success':True}

    js = json.dumps(results)
    return HttpResponse(js, content_type='application/json')    

def delete_release_task(request):
    release_id = request.GET['rel_id']
    task_id = request.GET['task_id']
    
    task = ReleaseTask.objects.get(id=task_id)
    task.delete()
    
    results = {'success':True}

    js = json.dumps(results)
    return HttpResponse(js, content_type='application/json')    
