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

from django import forms
from django.shortcuts import redirect, render

from stratosource.management import Utils
from stratosource.models import Branch, BranchLog, Repo, DeployableObject, Delta, EmailTemplateFolder
from ss2 import settings
from django.core.exceptions import ObjectDoesNotExist
from crontab import CronTab, CronItem
from django.db import transaction
import subprocess
import os
import re
import logging

logger = logging.getLogger('console')
CRON_COMMENT = 'StratoSource ID'


class RepoForm(forms.ModelForm):
    class Meta:
        model = Repo
        fields = '__all__'

    def clean(self):

        cleaned_data = self.cleaned_data
#        path = cleaned_data.get("location")
        name = cleaned_data.get("name")
        path = os.path.join('/var/sfrepo', name, 'code')
 #       cleaned_data['location'] = path

        if not os.path.isdir(path):
            try:
                os.makedirs(path)
            except Exception as ex:
                self.errors['__all__'] = self.error_class([str(ex)])
#                self._errors["location"] = self.error_class(['Path does not exist and unable to create'])
                return cleaned_data

            if os.path.isdir(path):
                curdir = os.getcwd()
                os.chdir(path)
                try:
                    #
                    # initialize the git repo
                    #
                    output = subprocess.check_output(['/usr/bin/git','init'])
                    subprocess.check_output(['touch','.gitignore'])
                    subprocess.check_output(['/usr/bin/git', 'config', 'user.email', '"me@example.com"'])
                    subprocess.check_output(['/usr/bin/git', 'config', 'user.name', '"me"'])
                    subprocess.check_output(['/usr/bin/git', 'add','.gitignore'])
                    subprocess.check_output(['/usr/bin/git','commit','-m','"initial commit"'])
                except Exception as ex:
#                    self._errors["name"] = self.error_class(['Unable to create git repository in ' + path])
                    self._errors["name"] = self.error_class(['Unable to create git repository in ' + path, str(ex)])
                finally:
                    os.chdir(curdir)
        return cleaned_data


class BranchForm(forms.ModelForm):
    SFENVCHOICES = (
        ('test', 'Test/Sandbox'),
        ('login', 'Production'),
    )
    SFAPIASSETS = (
        ('CustomPageWebLink', 'Custom page web links'),
        ('CustomLabels', 'Custom labels'),
        ('CustomApplication', 'Custom applications'),
        ('CustomObject', 'Custom objects and fields'),
        ('CustomObjectTranslation', 'Custom object translations'),
        ('Translations', 'Translations'),
        ('CustomSite', 'Sites'),
        ('CustomTab', 'Tabs'),
        ('DataCategoryGroup', 'Category groups'),
        ('EmailTemplate', 'Email templates'),
        ('HomePageLayout', 'Home page layout'),
        ('GlobalPicklist', 'Global Picklist'),
        ('Layout', 'Layouts'),
        ('Portal', 'Portal'),
        ('Profile', 'Profiles'),
        ('RecordType', 'Record types'),
        ('RemoteSiteSetting', 'Remote site settings'),
        ('HomePageComponent', 'Home page components'),
        ('ArticleType', 'Article types'),
        #('ApexPage', 'Pages'),
        #('ApexClass', 'Classes'),
        #('ApexTrigger', 'Triggers'),
        #('ApexComponent', 'Apex Components'),
        ('ReportType', 'Report types'),
        ('Scontrol', 'S-Controls'),
        ('ConnectedApp', 'Connected Apps'),
        ('CustomPageWebLink', 'Custom Page Web Links'),
        ('PermissionSet', 'Permission Sets'),
        ('ExternalDataSource', 'External Data Sources'),
        #        ('StaticResource', 'Static resources'),
        ('Workflow', 'Workflows'),
        ('ApprovalProcess', 'Approval processes'),
        ('EntitlementTemplate', 'Entitlement templates'),
    )

    api_env = forms.ChoiceField(choices=SFENVCHOICES)
    api_assets = forms.MultipleChoiceField(choices=SFAPIASSETS, required=False)
    #    api_pass = forms.CharField(max_length=100, widget=forms.PasswordInput)
    api_pass2 = forms.CharField(max_length=100, widget=forms.PasswordInput, required=False)

    class Meta:
        model = Branch
        fields = '__all__'
        widgets = {
            'api_pass': forms.widgets.PasswordInput(),
        }

    def clean(self):

        cleaned_data = self.cleaned_data
        #        api_ver = cleaned_data.get("api_ver")
        #        if api_ver and not re.match('^\d\d\.\d', api_ver):
        #           self._errors["api_ver"] = self.error_class(['Invalid API Version - use xx.x format']);

        name = cleaned_data.get("name")
        if name and not re.match('^\w+$', name):
            self._errors["name"] = self.error_class(['Invalid branch name - use only alphanumeric'])

        repo = cleaned_data.get("repo")
        if not repo:
            self._errors["repo"] = self.error_class(['Choose a repository'])

        pass1 = cleaned_data.get("api_pass")
        pass2 = cleaned_data.get("api_pass2")

        if pass1 and pass2 and pass1 != pass2:
            self._errors["api_pass"] = self.error_class(['Passwords do not match'])
            self._errors["api_pass2"] = self.error_class(['Passwords do not match'])

        cron_type = cleaned_data.get('cron_type')
        cron_interval = int(cleaned_data.get('cron_interval'))
        cron_start = cleaned_data.get('cron_start')
        order = cleaned_data.get('order')
        if cron_type == 'h':
            if cron_interval < 1 or cron_interval > 23:
                self._errors["cron_interval"] = self.error_class(['Interval must be between 1 and 23'])
            offset = int(cron_start)
            if offset < 0 or offset > 59:
                self._errors["cron_start"] = self.error_class(['Start must be between 0 and 59'])

        return cleaned_data


def newbranch(request):
    if request.method == 'POST':
        form = BranchForm(request.POST)

        if form.is_valid():
            # Process the data in form.cleaned_data
            row = Branch()
            cleaned_data = form.cleaned_data
            row.repo = cleaned_data.get('repo')
            row.name = cleaned_data.get('name')
            row.api_env = cleaned_data.get('api_env')
            row.api_user = cleaned_data.get('api_user')
            row.api_pass = cleaned_data.get('api_pass')
            row.api_auth = cleaned_data.get('api_auth')
            row.api_store = cleaned_data.get('api_store')
            #            row.api_ver = cleaned_data.get('api_ver')
            row.api_assets = ','.join(cleaned_data.get('api_assets'))
            row.save()

            createCrontab(row)
            createCGitEntry(row)

            repo = Repo.objects.get(id=row.repo_id)
            curdir = os.getcwd()
            os.chdir(repo.location)
            try:
                #
                # initialize the git repo
                #
                subprocess.check_output(['git', 'checkout', '-b', row.name, 'master'])
            except Exception as ex:
                removeCGitEntry(row)
                removeCrontab(row)
                row.delete()
                logger.exception(ex)
                raise
            finally:
                os.chdir(curdir)

            if 'EmailTemplate' in row.api_assets:
                return edit_branch_details(request, row.id, True)

            return adminMenu(request)
    else:
        form = BranchForm()
    return render(request, 'editbranch.html', {'form': form, 'type': 'New', 'action': 'newbranch/'})


def editbranch(request, branch_id):
    if request.method == 'POST':
        if 'cancelButton' in request.POST:
            return adminMenu(request)
        form = BranchForm(request.POST)
        if form.is_valid():
            # Process the data in form.cleaned_data
            row = Branch.objects.get(id=branch_id)
            cleaned_data = form.cleaned_data
            row.repo = cleaned_data.get('repo')
            row.name = cleaned_data.get('name')
            row.api_env = cleaned_data.get('api_env')
            row.api_user = cleaned_data.get('api_user')
            api_pass = cleaned_data.get('api_pass')
            if api_pass and len(api_pass) > 0:
                row.api_pass = api_pass
            row.api_auth = cleaned_data.get('api_auth')
            row.api_store = cleaned_data.get('api_store')
            #            row.api_ver = cleaned_data.get('api_ver')
            row.api_assets = ','.join(cleaned_data.get('api_assets'))
            row.enabled = cleaned_data.get('enabled')
            row.cron_enabled = cleaned_data.get('cron_enabled')
            row.cron_type = cleaned_data.get('cron_type')
            row.cron_interval = cleaned_data.get('cron_interval')
            row.cron_start = cleaned_data.get('cron_start')
            row.code_cron_enabled = cleaned_data.get('code_cron_enabled')
            row.code_cron_type = cleaned_data.get('code_cron_type')
            row.code_cron_interval = cleaned_data.get('code_cron_interval')
            row.code_cron_start = cleaned_data.get('code_cron_start')
            row.order = cleaned_data.get('order')
            row.save()
            updateCrontab(row)
            createCGitEntry(row)
            if 'EmailTemplate' in row.api_assets:
                return edit_branch_details(request, branch_id, True)
            return adminMenu(request)
        else:
            logger.debug(form.errors)
    else:
        row = Branch.objects.get(id=branch_id)
        row.api_assets = row.api_assets.split(',')
        form = BranchForm(instance=row)
    return render(request, 'editbranch.html', {'form': form, 'type': 'Edit', 'action': 'editbranch/' + branch_id})

@transaction.atomic
def edit_branch_details(request, branch_id, from_edit = False):

    branch = Branch.objects.get(id=branch_id)
    selected = EmailTemplateFolder.objects.filter(branch=branch).order_by('name')

    if not from_edit and request.method == 'POST' and request.POST.__contains__('saveFoldersButton'):
        folderlist = request.POST.getlist('email_template_folder')
        for select in selected: select.delete()
        for folder in folderlist:
            ef = EmailTemplateFolder()
            ef.branch = branch
            ef.name = folder
            ef.save()
        return adminMenu(request)

    try:
        agent = Utils.getAgentForBranch(branch)
        folders = agent.getSalesforceEmailTemplateFolders()
    except Exception as ex:
        return render(request, 'error.html', {'error_message': str(ex) })

    folders.sort()
    for select in selected:
        if select.name in folders:
            folders.remove(select.name)

    return render(request, 'edit_asset_details.html', {'branch': branch, 'selected': selected, 'folders': folders})


def last_log(request, branch_id, logtype):
    branch = Branch.objects.get(id=branch_id)
    log = 'No Log Found'
    try:
        branchlog = BranchLog.objects.get(branch=branch, logtype=logtype)
        log = branchlog.lastlog
    except ObjectDoesNotExist:
        pass

    data = {'branch': branch, 'log': log}
    return render(request, 'last_log.html', data)

#
# just-in-time setup of cgit config, to support Docker
#
def verifyCgit():
    if not os.path.isdir(settings.CONFIG_DIR):
        os.mkdir(settings.CONFIG_DIR)
    if not os.path.isfile(os.path.join(settings.CONFIG_DIR, 'cgitrepo')):
        subprocess.check_output(['cp', os.path.join(settings.BASE_DIR, 'resources', 'cgitrepo'), settings.CONFIG_DIR])

def createCGitEntry(branch):
    verifyCgit()
    removeCGitEntry(branch)
    f = open(os.path.join(settings.CONFIG_DIR, 'cgitrepo'), 'a')
    f.write('#ID=%d\n' % branch.id)
    f.write('repo.url=%s\n' % branch.name)
    f.write('repo.path=%s/.git\n' % branch.repo.location)
    f.write('repo.desc=%s\n' % branch.name)
    f.close()


def removeCGitEntry(branch):
    verifyCgit()
    p = os.path.join(settings.CONFIG_DIR, 'cgitrepo')
    if not os.path.exists(p):
        return
    f = open(p, 'r')
    lines = f.readlines()
    f.close()
    linecount = 0
    found = False
    prefix = '#ID=%d' % branch.id
    for line in lines:
        if line.startswith(prefix):
            found = True
            break
        linecount += 1
    if found:
        start = linecount
        linecount += 1
        while linecount < len(lines) and len(lines[linecount]) > 0 and lines[linecount][0:1] != '#': linecount += 1
        #        del lines[start:linecount]
        f = open(os.path.join(settings.CONFIG_DIR, 'cgitrepo'), 'w')
        f.writelines(lines[0:start])
        f.writelines(lines[linecount:])
        f.close()


def createCrontab(branch):
    ctab = CronTab()
    if branch.cron_enabled and branch.cron_type == 'h':
        if branch.cron_interval > 1:
            interval_list = [str(x) for x in range(0, 23, branch.cron_interval)]
            interval_str = ','.join(interval_list)
        else:
            interval_str = '*'
        cronline = "%s %s * * * %s %s %s >/var/sftmp/config_cronjob.out 2>&1" % (
            branch.cron_start, interval_str, os.path.join(settings.BASE_DIR, 'config_cronjob.sh'), branch.repo.name,
            branch.name)
        logger.debug('Creating cron tab with line ' + cronline)
        item = CronItem(line=cronline + ' #' + (CRON_COMMENT + ' %d' % branch.id))
        ctab.add(item)
        ctab.write()
    if branch.code_cron_enabled and branch.code_cron_type == 'h':
        if branch.code_cron_interval > 1:
            interval_list = [str(x) for x in range(0, 23, branch.code_cron_interval)]
            interval_str = ','.join(interval_list)
        else:
            interval_str = '*'
        cronline = "%s %s * * * %s %s %s >/var/sftmp/code_cronjob.out 2>&1" % (
            branch.code_cron_start, interval_str, os.path.join(settings.BASE_DIR, 'code_cronjob.sh'), branch.repo.name,
            branch.name)
        logger.debug('Creating cron tab with line ' + cronline)
        item = CronItem(line=cronline + ' #' + (CRON_COMMENT + ' %d' % branch.id))
        ctab.add(item)
        ctab.write()


def updateCrontab(branch):
    removeCrontab(branch)
    if branch.cron_enabled or branch.code_cron_enabled:
        return createCrontab(branch)


def removeCrontab(branch):
    ctab = CronTab()
    comment = CRON_COMMENT + ' %d' % branch.id
    theItems = []
    for item in ctab:
        if item.raw_line.find(comment) > -1:
            theItems.append(item)

    for theItem in theItems:
        ctab.remove(theItem)
        ctab.write()


def adminMenu(request):
    if request.method == u'GET' and request.GET.__contains__('reset') and request.GET['reset'] == 'true':
        snaptype = request.GET['type']
        branch_id = request.GET['branch_id']
        branch = Branch.objects.get(id=branch_id)
        if snaptype == 'config':
            branch.run_status = 'd'
        else:
            branch.code_run_status = 'd'
        branch.save()
        return redirect("/admin/?success=true")

    if request.method == u'GET' and request.GET.__contains__('snapshot') and request.GET['snapshot'] == 'true':
        branch_id = request.GET['branch_id']
        snaptype = request.GET['type']
        branch = Branch.objects.get(id=branch_id)
        if snaptype == 'config' and branch.run_status != 'r':
            repo_name = branch.repo.name
            branch_name = branch.name
            pr = subprocess.Popen(os.path.join(settings.BASE_DIR,
                                  'config_cronjob.sh') + ' ' + repo_name + ' ' + branch_name + ' >/var/sftmp/ssRun.out 2>&1 &',
                                  shell=True)
            logger.debug('Started With pid ' + str(pr.pid))
            pr.wait()
            if pr.returncode == 0:
                brlog = BranchLog()
                try:
                    brlog = BranchLog.objects.get(branch=branch, logtype=snaptype)
                except ObjectDoesNotExist:
                    brlog.branch = branch
                    brlog.logtype = snaptype
                brlog.last_log = 'Started'
                brlog.save()
                branch.run_status = 'r'
                branch.save()
                return redirect("/admin/?success=true")
            return redirect("/admin/?failed=true")
        if snaptype == 'code' and branch.code_run_status != 'r':
            repo_name = branch.repo.name
            branch_name = branch.name
            pr = subprocess.Popen(os.path.join(settings.BASE_DIR,
                                    'code_cronjob.sh') + ' ' + repo_name + ' ' + branch_name + ' >/var/sftmp/ssRun.out 2>&1 &',
                                    shell=True)
            logger.debug('Started With pid ' + str(pr.pid))
            pr.wait()
            if pr.returncode == 0:
                brlog = BranchLog()
                try:
                    brlog = BranchLog.objects.get(branch=branch, logtype=snaptype)
                except ObjectDoesNotExist:
                    brlog.branch = branch
                    brlog.logtype = snaptype
                brlog.last_log = 'Started'
                brlog.save()
                branch.code_run_status = 'r'
                branch.save()
                return redirect("/admin/?success=true")
            return redirect("/admin/?failed=true")

    repos = Repo.objects.all()
    branches = Branch.objects.all()
    ctab = CronTab()
    cronlist = []
    for item in [entry.render() for entry in ctab]:
        if item.find(CRON_COMMENT) != -1:
            cronlist.append(item)

    return render(request, 'admin_menu.html', {'repos': repos, 'branches': branches, 'crontab': cronlist})


def repo_form_action(request):
    if request.method == 'POST' and request.POST.__contains__('delRepoButton'):
        repolist = request.POST.getlist('repocb')
        if repolist:
            for repoid in repolist:
                branches = Branch.objects.filter(repo__id=repoid)
                for branch in branches:
                    removeCrontab(branch)
                    removeCGitEntry(branch)
                r = Repo.objects.get(id=repoid)
                brlist = Branch.objects.filter(repo=r)
                for br in brlist:
                    branchCascadeDelete(br)
                brlist.delete()
                r.delete()
    if request.method == 'POST' and request.POST.__contains__('addRepoButton'):
        return redirect('/newrepo')

    return adminMenu(request)


def branch_form_action(request):
    if request.method == 'POST' and request.POST.__contains__('delBranchButton'):
        branchlist = request.POST.getlist('branchcb')
        if branchlist:
            for branchid in branchlist:
                br = Branch.objects.get(id=branchid)
                removeCrontab(br)
                removeCGitEntry(br)
                branchCascadeDelete(br)
    if request.method == 'POST' and request.POST.__contains__('addBranchButton'):
        return redirect('/newbranch')

    return adminMenu(request)


def branchCascadeDelete(br):
    deplist = DeployableObject.objects.filter(branch=br)
    for dep in deplist:
        deltas = Delta.objects.filter(object=dep)
        deltas.delete()
    deplist.delete()
    BranchLog.objects.filter(branch=br).delete()
    br.delete()


def newrepo(request):
    if request.method == 'POST':
        form = RepoForm(request.POST)
        if form.is_valid():
            row = Repo()
            cleaned_data = form.cleaned_data
            row.name = cleaned_data.get('name')
            row.location = os.path.join('/var/sfrepo', row.name, 'code')
            row.save()
#            form.save()
            return adminMenu(request)
    else:
        form = RepoForm()
    return render(request, 'editrepo.html', {'form': form, 'type': 'New', 'action': 'newrepo/'})


def editrepo(request, repo_id):
    if request.method == 'POST':
        form = RepoForm(request.POST)
        if form.is_valid():
            row = Repo.objects.get(id=repo_id)
            cleaned_data = form.cleaned_data
            row.name = cleaned_data.get('name')
            #row.location = cleaned_data.get('location')
            row.location = os.path.join('/var/sfrepo', row.name, 'code')
            row.save()
            return adminMenu(request)
    else:
        form = RepoForm(instance=Repo.objects.get(id=repo_id))
    return render(request, 'editrepo.html', {'form': form, 'type': 'Edit', 'action': 'editrepo/' + repo_id})
