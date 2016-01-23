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
from django.shortcuts import render_to_response, redirect
from django import forms
from stratosource.models import UnitTestBatch, UnitTestRun, UnitTestRunResult, UnitTestSchedule
from ss2 import settings
from stratosource.admin.management import UnitTestRunUtil
from crontab import CronTab, CronItem
import logging
import os

from stratosource.user.admin_views import adminMenu

logger = logging.getLogger('console')

CRON_COMMENT = 'StratoSource Unit Test Schedule ID'


class UnitTestScheduleForm(forms.ModelForm):
    class Meta:
        model = UnitTestSchedule
        fields = '__all__'

    def clean(self):

        cleaned_data = self.cleaned_data
        branch = cleaned_data.get("branch")
        if not branch:
            self._errors["branch"] = self.error_class(['Choose a branch'])

        if self.is_new:
            already_scheduled = UnitTestSchedule.objects.filter(branch=branch)
            if len(already_scheduled) > 0:
                self._errors["branch"] = self.error_class([
                    'There is already a unit test schedule for this branch, only one schedule is allowed per branch'])

        cron_type = cleaned_data.get('cron_type')
        cron_interval = int(cleaned_data.get('cron_interval'))
        cron_start = cleaned_data.get('cron_start')
        if cron_type == 'h':
            if cron_interval < 1 or cron_interval > 23:
                self._errors["cron_interval"] = self.error_class(['Interval must be between 1 and 23'])
            offset = int(cron_start)
            if offset < 0 or offset > 59:
                self._errors["cron_start"] = self.error_class(['Start must be between 0 and 59'])

        return cleaned_data


def create_crontab(uts):
    ctab = CronTab()
    if uts.cron_type == 'h':
        if uts.cron_interval > 1:
            interval_list = [str(x) for x in range(0, 23, uts.cron_interval)]
            interval_str = ','.join(interval_list)
        else:
            interval_str = '*'
        cronline = "%s %s * * * %s runtests %s %s >/tmp/unitTestCronjob%s.out 2>&1" % (
            uts.cron_start, interval_str, os.path.join(settings.BASE_DIR, 'runmanage.sh'), uts.branch.repo.name,
            uts.branch.name, uts.id)
        logger.debug('Creating cron tab with line ' + cronline)
        item = CronItem(line=cronline + ' #' + ('%s %d' % (CRON_COMMENT, uts.id)))
        ctab.add(item)
        ctab.write()


def update_crontab(uts):
    remove_crontab(uts)
    if uts.cron_enabled:
        return create_crontab(uts)


def remove_crontab(uts):
    ctab = CronTab()
    comment = CRON_COMMENT + ' %d' % uts.id
    theitem = None
    for item in ctab:
        if item.raw_line.find(comment) > -1:
            theitem = item
            break

    if theitem:
        ctab.remove(theitem)
        ctab.write()


def admin(request):
    schedules = UnitTestSchedule.objects.all()
    schedules.select_related()

    ctab = CronTab()
    cronlist = []
    for item in [entry.render() for entry in ctab]:
        if item.find(CRON_COMMENT) != -1:
            cronlist.append(item)

    data = {'schedules': schedules, 'crontab': cronlist}
    return render_to_response('unit_test_config.html', data, context_instance=RequestContext(request))


def results(request):
    batches = UnitTestBatch.objects.all().order_by('-batch_time')[:50]

    if request.method == 'GET' and request.GET.__contains__('sendReport'):
        batch_id = request.GET['sendReport']
        UnitTestRunUtil.process_run(batch_id)

    data = {'batches': batches}
    return render_to_response('unit_testing_results.html', data, context_instance=RequestContext(request))


def ajax_unit_test_resultslist(request, batch_id):
    batch = UnitTestBatch.objects.get(id=batch_id)
    runs = UnitTestRun.objects.filter(batch=batch).order_by('class_name')

    for run in runs:
        run.successful = run.failures == 0
        if run.successful:
            if run.failures == 0:
                run.outcome = str(run.tests) + ' Tests Passed'
            if run.tests == 0:
                run.outcome = 'No Results'
        else:
            run.outcome = str(run.failures) + ' of ' + str(run.tests) + ' Tests Failed'

    data = {'batch': batch, 'runs': runs}
    return render_to_response('ajax_unit_testing_batch_list.html', data, context_instance=RequestContext(request))


def result(request, run_id):
    run = UnitTestRun.objects.get(id=run_id)
    ut_results = UnitTestRunResult.objects.filter(test_run=run)

    data = {'run': run, 'results': ut_results}
    return render_to_response('unit_testing_result.html', data, context_instance=RequestContext(request))


def new_test_schedule(request):
    if request.method == 'POST':
        form = UnitTestScheduleForm(request.POST)
        form.is_new = True
        if form.is_valid():
            row = UnitTestSchedule()
            cleaned_data = form.cleaned_data
            row.branch = cleaned_data.get('branch')
            row.results_email_address = cleaned_data.get('results_email_address')
            row.email_only_failures = cleaned_data.get('email_only_failures')
            row.cron_enabled = cleaned_data.get('cron_enabled')
            row.cron_type = cleaned_data.get('cron_type')
            row.cron_interval = cleaned_data.get('cron_interval')
            row.cron_start = cleaned_data.get('cron_start')
            row.save()
            create_crontab(row)
            return admin(request)
    else:
        form = UnitTestScheduleForm()
    return render_to_response('edit_unit_testing_schedule.html',
                              {'form': form, 'type': 'New', 'action': 'new_test_schedule/'},
                              context_instance=RequestContext(request))


def edit_test_schedule(request, uts_id):
    if request.method == 'POST':
        form = UnitTestScheduleForm(request.POST)
        form.is_new = False
        if form.is_valid():
            row = UnitTestSchedule.objects.get(id=uts_id)
            cleaned_data = form.cleaned_data
            row.branch = cleaned_data.get('branch')
            row.results_email_address = cleaned_data.get('results_email_address')
            row.email_only_failures = cleaned_data.get('email_only_failures')
            row.cron_enabled = cleaned_data.get('cron_enabled')
            row.cron_type = cleaned_data.get('cron_type')
            row.cron_interval = cleaned_data.get('cron_interval')
            row.cron_start = cleaned_data.get('cron_start')
            row.save()

            update_crontab(row)

            return admin(request)
    else:
        form = UnitTestScheduleForm(instance=UnitTestSchedule.objects.get(id=uts_id))

    return render_to_response('edit_unit_testing_schedule.html',
                              {'form': form, 'type': 'Edit', 'action': 'edit_test_schedule/' + uts_id},
                              context_instance=RequestContext(request))


def unit_test_schedule_admin_form_action(request):
    if request.method == 'GET' and request.GET.__contains__('deleteSchedule'):
        scheduleid = request.GET.get('scheduleId')
        if scheduleid:
            uts = UnitTestSchedule.objects.get(id=scheduleid)
            remove_crontab(uts.branch)
            uts.delete()
    if request.method == 'POST' and request.POST.__contains__('addScheduledTestButton'):
        return redirect('/new_test_schedule')

    return adminMenu(request)
