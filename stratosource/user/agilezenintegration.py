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

import requests
from stratosource.admin.management import ConfigCache
from stratosource.models import Story
import logging
from django.db import transaction

agilezen_apikey = ConfigCache.get_config_value('agilezen.apikey')
rest_header = {"X-Zen-ApiKey": agilezen_apikey, "Accept" : "application/json;charset=utf-8"}
logger = logging.getLogger('console')    
agileurl = 'https://agilezen.com/'
apiurl = 'api/v1/'

def print_proj_tree(pList):
    for p in pList:
        logger.debug('%d - %s - %s' % (p[u'id'] , p[u'name'] , p[u'owner']))
        
def get_page_query_params(page, page_size):
    return "page=%d&pageSize=%d" % (page, page_size)

def get_projects(leaves):
    logger.debug('Start getting projects')
    projurl = agileurl+apiurl+'projects'  #?' #+ get_page_query_params(1, 200)
    logger.debug('Retrieving Projects from URL: '+projurl)
    response = requests.get(projurl, headers=rest_header)
    
    project_list = {}
    try:
        project_list = (response.json())[u'items']
        print_proj_tree(project_list)
    except:
        logger.debug('No Results Returned')
 
    return project_list

def get_stories(projectIds):
    stories = {}
    start = 1
    pagesize = 200
    for projId in projectIds:
        lastPage = False
        page = start
        while not(lastPage):
            storyurl = agileurl+apiurl+'projects/'+ projId +'/stories?'+ get_page_query_params(page, pagesize)
            logger.debug('Retrieving Stories from URL: '+storyurl)
            response = requests.get(storyurl, headers=rest_header)
            processed_response = response.json()
            story_list = processed_response[u'items']
            count = len(story_list) #processed_response[u'totalItems']

            for result in story_list:
                #print result
                phase = result[u'phase']
                ignorestates = [u'Backlog', u'Ready', u'Archive',  u'Release Candidate / Production']
                if not phase[u'name'] in ignorestates:
                    story = Story()
                    story.rally_id = result[u'id']
                    story.name = result[u'text'][0:100]
                    story.sprint = result[u'text'][0:3]
                    story.url = agileurl+'project/'+ projId +'/story/%d'%result[u'id']
                    try:
                        story.sprint = '%s - %s' % (projId, result[u'deadline'])
                        #story.release_date = result[u'deadline']
                    except:
                        story.sprint = '%s'%projId
                        logger.debug('no deadline for story %d'%story.rally_id)
                    stories[story.rally_id] = story
                    
            if count == 0:
                lastPage = True
            page += 1
            
    return stories

@transaction.atomic
def refresh():
        projectList = ConfigCache.get_config_value('rally.pickedprojects')
        #print 'project list: '+projectList
        if len(projectList) > 0:
            rallyStories = get_stories(projectList.split(';'))
            dbstories = Story.objects.filter(rally_id__in=rallyStories.keys())
            dbStoryMap = {}
            for dbstory in dbstories:
                #print 'storing story %d' % int(dbstory.rally_id)
                dbStoryMap[int(dbstory.rally_id)] = dbstory

            for story in rallyStories.values():
                dbstory = story
                if story.rally_id in dbStoryMap:
                    #print 'match found %d' % story.rally_id
                    logger.debug('Updating [%d]' % story.rally_id)
                    # Override with database version if it exists
                    dbstory = dbStoryMap[story.rally_id]
                    dbstory.url = story.url
                    dbstory.name = story.name
                    dbstory.sprint = story.sprint
                else:
                    #print 'no match found %d' % story.rally_id
                    logger.debug('Creating [%d]' % story.rally_id)
                    dbstory.sprint = story.sprint
                
                dbstory.save()
