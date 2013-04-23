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
from django.conf.urls.defaults import *

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

import os

PROJECT_PATH = os.path.abspath(os.path.split(__file__)[0])

urlpatterns = patterns('',
    # Example:
    # (r'^stratosource/', include('stratosource.admin.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    #(r'^admin/', include(admin.site.urls)),
    (r'^djadmin/', include(admin.site.urls)),

    (r'^$', 'stratosource.user.views.home'),
    (r'^configs/', 'stratosource.user.views.configs'),
    (r'^unit_testing_results/', 'stratosource.user.unit_testing_views.results'),
    (r'^unit_testing_result/(.+)$', 'stratosource.user.unit_testing_views.result'),
    (r'^ajax/unit_testing_result_list/(\d+)$', 'stratosource.user.unit_testing_views.ajax_unit_test_resultslist'),
    (r'^unit_testing_admin/', 'stratosource.user.unit_testing_views.admin'),
    (r'^unit_test_schedule_admin_form_action', 'stratosource.user.unit_testing_views.unit_test_schedule_admin_form_action'),
    (r'^new_test_schedule/', 'stratosource.user.unit_testing_views.new_test_schedule'),
    (r'^edit_test_schedule/(\d+)$', 'stratosource.user.unit_testing_views.edit_test_schedule'),
    (r'^rally_projects/', 'stratosource.user.views.rally_projects'),
    (r'^manifest/(.+)$', 'stratosource.user.views.manifest'),
    (r'^exportlabels/(.+)$', 'stratosource.user.views.export_labels'),
    (r'^export_labels_form', 'stratosource.user.views.export_labels_form'),
    (r'^release_create_package/(.+)$', 'stratosource.user.views.create_release_package'),
    (r'^release_package/(.+)$', 'stratosource.user.views.release_package'),
    (r'^release_delete_package/(.+)$', 'stratosource.user.views.delete_release_package'),    
    (r'^release_push_package/(.+)$', 'stratosource.user.views.push_release_package'),
    (r'^release_push_status/(.+)$', 'stratosource.user.views.release_push_status'),    
    (r'^releases', 'stratosource.user.views.releases'),
    (r'^release/(.+)$', 'stratosource.user.views.release'),
    (r'^unreleased/(.+)/(.+)$', 'stratosource.user.views.unreleased'),
    (r'^object/(\d+)$', 'stratosource.user.views.object'),
    (r'^stories', 'stratosource.user.views.stories'),
    (r'^instory/(\d+)$', 'stratosource.user.views.instory'),
    (r'^ajax/releases', 'stratosource.user.ajax.releases'),
    (r'^ajax/createrelease', 'stratosource.user.ajax.createrelease'),
    (r'^ajax/deleterelease', 'stratosource.user.ajax.deleterelease'),
    (r'^ajax/markreleased', 'stratosource.user.ajax.markreleased'),
    (r'^ajax/getstories', 'stratosource.user.ajax.getstories'),
    (r'^ajax/getsprints', 'stratosource.user.ajax.getsprints'),
    (r'^ajax/addtostory', 'stratosource.user.ajax.addtostory'),
    (r'^ajax/updaterelease', 'stratosource.user.ajax.updaterelease'),
    (r'^ajax/ignoreitem/(\d+)$', 'stratosource.user.ajax.ignoreitem'),
    (r'^ajax/ignoreselected', 'stratosource.user.ajax.ignoreselected'),
    (r'^ajax/ignoretranslation/(\d+)$', 'stratosource.user.ajax.ignoretranslation'),
    (r'^ajax/addreleasetask', 'stratosource.user.ajax.add_release_task'),
    (r'^ajax/editreleasetask', 'stratosource.user.ajax.edit_release_task'),
    (r'^ajax/delreleasetask', 'stratosource.user.ajax.delete_release_task'),
    (r'^ajax/reorderreleasetasks', 'stratosource.user.ajax.reorder_release_tasks'),
    (r'^ajax/releasetasks/(.)(\d+)$', 'stratosource.user.ajax.get_release_tasks'),

    (r'^repos/', 'stratosource.admin.views.repos'),
    (r'^branches/(\d+)$', 'stratosource.admin.views.branches'),
    (r'^commits/(\d+)$', 'stratosource.admin.views.commits'),
    (r'^commit/(\d+)$', 'stratosource.admin.views.commit'),

    (r'^csmedia/(?P<path>.*)$', 'django.views.static.serve',
        {'document_root': os.path.join(PROJECT_PATH, 'csmedia')}),

    # admin menu support
    (r'^admin/', 'stratosource.user.admin_views.adminMenu'),
    (r'^lastlog/(\d+)$', 'stratosource.user.admin_views.last_log'),
    (r'^newbranch/', 'stratosource.user.admin_views.newbranch'),
    (r'^editbranch/(\d+)$', 'stratosource.user.admin_views.editbranch'),
    (r'^repo_admin_form_action', 'stratosource.user.admin_views.repo_form_action'),
    (r'^branch_admin_form_action', 'stratosource.user.admin_views.branch_form_action'),
    (r'^newrepo/', 'stratosource.user.admin_views.newrepo'),
    (r'^editrepo/(\d+)$', 'stratosource.user.admin_views.editrepo'),
    (r'^repo_form_action', 'stratosource.user.admin_views.repo_form_action'),
)
