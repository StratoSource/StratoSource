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

from django.db import transaction
from django.core.mail import EmailMultiAlternatives
from django.core import mail
from django.template import Context
from django.template.loader import get_template
from stratosource.models import UnitTestBatch, UnitTestRun, UnitTestRunResult, UnitTestSchedule
from stratosource.management import ConfigCache
from django.core.exceptions import ObjectDoesNotExist
import logging

logger = logging.getLogger('console')


def email_results(batch, failures, runs):
    long_runners = UnitTestRunResult.objects.filter(test_run__in=runs).order_by('-runtime')[:5]
    long_runners.select_related()
    long_runner_classes = UnitTestRun.objects.filter(batch=batch).order_by('-runtime')[:5]
    long_runner_classes.select_related()

    try:
        schedule = UnitTestSchedule.objects.get(branch=batch.branch)
    except ObjectDoesNotExist:
        logger.error(
                'No Schedule exists for this branch (' + batch.branch.name + '), so no way to figure out who to email')
        return

    email_host = ConfigCache.get_config_value('email.host')
    conn = mail.get_connection(host=email_host)

    from_address = ConfigCache.get_config_value('email.from')

    if schedule.email_only_failures and len(failures) == 0:
        return

    template = get_template('unit_test_results_email.html')
#    c = Context({'batch': batch, 'failures': failures, 'long_runners': long_runners,
#                 'long_runner_classes': long_runner_classes})
    c = {'batch': batch, 'failures': failures, 'long_runners': long_runners,
                 'long_runner_classes': long_runner_classes}

    subject = 'Unit test results for ' + batch.branch.name.upper() + ' started at ' + str(batch.batch_time)
    from_email, to = from_address, schedule.results_email_address
    text_content = 'Please join the 21st century and get an HTML compatible email client to see the content of this email.'
    html_content = template.render(c)
    msg = EmailMultiAlternatives(subject, text_content, from_email, [to])
    msg.attach_alternative(html_content, "text/html")
    msg.connection = conn
    msg.send(fail_silently=False)


@transaction.atomic
def process_run(batch_id):
    failures = []

    batch = UnitTestBatch.objects.get(id=batch_id)
    batch.runtime = 0
    batch.tests = 0
    batch.failures = 0

    runs = UnitTestRun.objects.filter(batch=batch)
    for run in runs:
        run.runtime = 0
        results = UnitTestRunResult.objects.filter(test_run=run)

        for result in results:
            # For each result, calculate the time taken - minimum 1 second
            if result.outcome == 'Pass':
                if result.end_time == result.start_time:
                    result.runtime = 1
                else:
                    td = result.end_time - result.start_time
                    result.runtime = (td.microseconds + (td.seconds + td.days * 24 * 3600) * 10 ** 6) / 10 ** 6
            else:
                failures.append(result)

            # Save the result with time calculated
            result.save()
            # Add the result runtime to the test run
            run.runtime = int(run.runtime) + result.runtime

            # Save the run
        run.save()
        # Add the run's runtime to the batch
        batch.tests = int(batch.tests) + run.tests
        batch.failures = int(batch.failures) + run.failures
        batch.runtime = int(batch.runtime) + run.runtime

    # Save the batch
    batch.save()

    email_results(batch, failures, runs)

@transaction.atomic
def delete_batch(batch_id):
    batch = UnitTestBatch.objects.get(id=batch_id)
    # remove the batch, let cascading take out all the child records
    batch.delete()
