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
from stratosource.admin.management import ConfigCache
from stratosource.models import Story
from ss2 import settings
from operator import attrgetter
import logging
from django.db import transaction
from pyral import Rally


RALLY_REST_HEADERS = \
    {
      'User-Agent'                 : 'Pyral Rally WebServices Agent',
    }


logger = logging.getLogger('console')

class RallyProject():
    def __init__(self, a_name, a_url, some_children, some_sprints):
        self.name = a_name
        self.url = a_url
        url_pieces = a_url.split('/')
        jsFileName = url_pieces[len(url_pieces) - 1]
        jsFileNameParts = jsFileName.split('.')
        self.id = jsFileNameParts[0]
        self.children = some_children
        self.sprints = some_sprints

def print_proj_tree(pList):
    for p in pList:
        if len(p.children) == 0:
            logger.debug(p.name + ' - ' + p.id + ' (' + str(len(p.sprints)) + ' sprints)')
        else:
            print_proj_tree(p.children)

def find_leaves(pList, level, leaves):
    for p in pList:
        if len(p.children) == 0:
            if not leaves.has_key(p.id) or level > leaves[p.id]:
                leaves[p.id] = level
        else:
            find_leaves(p.children, level + 1, leaves)
    return leaves

def leaf_list(pList, llist):

    for p in pList:
        if len(p.children) == 0:
            llist.append(p)
        else:
            leaf_list(p.children, llist)

    return llist

def load_projects(session, name, projectList):
    projects = []
    if len(name) > 0:
        name = name + ': '
        
    if len(projectList) > 0:
        for project in projectList:
            projectDetail = project  # session.get('Project', query='ObjectID = "' + project + '"', fetch=True)
            print(project.Name)
            #print('Project Details:')
            #pprint(projectDetail.__dict__)
            proj = RallyProject(name + projectDetail.Name, projectDetail._ref, list(projectDetail.Children), list(projectDetail.Iterations))
            if len(proj.children) > 0 or len(proj.sprints) > 0:
                projects.append(proj)

    leaves = find_leaves(projects, 0, {})
    for p in projects:
        if  leaves.has_key(p.id) and leaves[p.id] > 0:
            projects.remove(p)

    projects.sort()

    return projects

def connect():
    rally_user = ConfigCache.get_config_value('rally.login')
    rally_pass = ConfigCache.get_config_value('rally.password')
    session = Rally(settings.RALLY_SERVER, rally_user, rally_pass)
    logger.debug('Logging in with username ' + rally_user)
    return session

def get_projects(leaves):
    logger.debug('Start getting projects')
    session = connect()

    # Get workspace:
    projects = []
    workspaces = session.getWorkspaces()

    for ws in workspaces:
#        fetchedProjects = session.get('Project', query='Workspace.ObjectID = "%s"' % (ws.ObjectID,), fetch=True)
#        print('Workspace: ' + ws.Name + ' url "' + ws._ref + '"' + ', projects=%d' % (len(list(fetchedProjects)),))
        projects.extend(load_projects(session, ws.Name, list(ws.Projects)))

    print_proj_tree(projects)
    if leaves:
        return sorted(leaf_list(projects,[]), key=attrgetter('name'))
    
    return projects  


def get_stories(projectIds):
    session = connect()

#    for project in session.getProjects():
#        print('name=' + project.Name)
#        print(project)

    stories = {}
#    projNames = ['Red Hat Connect Tech Partner Hub']
#    projectIds = ['c97fae21-9861-496d-8643-74adc92a00bc']

    for projectid in projectIds:
        print('projectid=%s' % (projectid,))
        queriedStories = session.get('Story', query='Project.ObjectID = "' + projectid + '"', fetch=True)
        queriedDefects = session.get('Defect', query='Project.ObjectID = "' + projectid + '"', fetch=True)
        queriedStories = list(queriedStories)
        queriedDefects = list(queriedDefects)
        for result in queriedStories + queriedDefects:
            story = Story()
            story.rally_id = result.FormattedID
            story.name = result.Name
            if result.Iteration:
                story.sprint = result.Iteration.Name
            stories[story.rally_id] = story

    print('finished get_stories(). count is %d' % (len(stories),))
    return stories

@transaction.atomic
def refresh():
        projectList = ConfigCache.get_config_value('rally.pickedprojects')
        logger.debug('projectList:')
        logger.debug(projectList)
        if len(projectList) > 0:
            rallyStories = get_stories(projectList.split(';'))
            dbstories = Story.objects.filter(rally_id__in=rallyStories.keys())
            dbStoryMap = {}
            for dbstory in dbstories:
                dbStoryMap[dbstory.rally_id] = dbstory

            for story in rallyStories.values():
                dbstory = story
                if story.rally_id in dbStoryMap:
                    #logger.debug('Updating [' + story.rally_id + ']')
                    # Override with database version if it exists
                    dbstory = dbStoryMap[story.rally_id]
                    dbstory.name = story.name
                #else:
                    #logger.debug('Creating [' + story.rally_id + ']')
                    
                dbstory.sprint = story.sprint
                dbstory.save()

