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
from django.template import RequestContext
from django.shortcuts import render_to_response
from stratosource.models import Repo, Branch, Commit, Delta, TranslationDelta



def repos(request):
    data = {'repos': Repo.objects.all() }
    return render_to_response('repos.html', data, context_instance=RequestContext(request))

def branches(request, repo_id):
    repo = Repo.objects.get(id=repo_id)
    branches = Branch.objects.filter(repo=repo)
    data = {'repo': repo, 'branches':branches }
    return render_to_response('branches.html', data, context_instance=RequestContext(request))

def commits(request, branch_id):
    branch = Branch.objects.get(id=branch_id)
    commits = Commit.objects.filter(branch=branch).order_by('-date_added')

    for commit in commits:
        adds = Delta.objects.filter(commit=commit,delta_type__exact='a').count() + \
               TranslationDelta.objects.filter(commit=commit,delta_type__exact='a').count()
        dels = Delta.objects.filter(commit=commit,delta_type__exact='d').count() + \
               TranslationDelta.objects.filter(commit=commit,delta_type__exact='d').count()
        updt = Delta.objects.filter(commit=commit,delta_type__exact='u').count() + \
               TranslationDelta.objects.filter(commit=commit,delta_type__exact='u').count()
        commit.__dict__['adds'] = adds
        commit.__dict__['dels'] = dels
        commit.__dict__['updt'] = updt
    data = {'branch': branch, 'commits':commits }
    return render_to_response('commits.html', data, context_instance=RequestContext(request))

def commit(request, commit_id):
    commit = Commit.objects.get(id=commit_id)
    deltas = Delta.objects.filter(commit=commit).order_by('object__type','object__filename','object__el_type','object__el_subtype','object__el_name','commit__date_added')
    data = {'commit': commit, 'deltas':deltas }
    for delta in deltas:
        delta.__dict__['type'] = delta.object.type
        delta.__dict__['filename'] = delta.object.filename
        delta.__dict__['el_name'] = delta.object.el_name
    return render_to_response('commit.html', data, context_instance=RequestContext(request))

