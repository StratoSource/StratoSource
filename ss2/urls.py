"""ss2 URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.8/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Add an import:  from blog import urls as blog_urls
    2. Add a URL to urlpatterns:  url(r'^blog/', include(blog_urls))
"""
from django.conf.urls import include, url
#from django.contrib import admin
import os

import stratosource.user.views
import stratosource.user.ajax
import stratosource.user.unit_testing_views
import stratosource.admin.views
import stratosource.user.admin_views
import stratosource.user.setup_views

urlpatterns = [
#    url(r'^djadmin/', include(admin.site.urls)),

    url(r'^$', stratosource.user.views.home),
    url(r'^setup/(?P<stage>\d+)$', stratosource.user.setup_views.setup),
    url(r'^configs/', stratosource.user.views.configs),
    url(r'^unit_testing_results/', stratosource.user.unit_testing_views.results),
    url(r'^unit_testing_result/(.+)$', stratosource.user.unit_testing_views.result),
    url(r'^ajax/unit_testing_result_list/(\d+)$', stratosource.user.unit_testing_views.ajax_unit_test_resultslist),
    url(r'^unit_testing_admin/', stratosource.user.unit_testing_views.admin),
    url(r'^unit_test_schedule_admin_form_action', stratosource.user.unit_testing_views.unit_test_schedule_admin_form_action),
    url(r'^new_test_schedule/', stratosource.user.unit_testing_views.new_test_schedule),
    url(r'^edit_test_schedule/(\d+)$', stratosource.user.unit_testing_views.edit_test_schedule),
    url(r'^rally_projects/', stratosource.user.views.rally_projects),
    url(r'^manifest/(.+)$', stratosource.user.views.manifest),
    #url(r'^exportlabels/(.+)$', stratosource.user.views.export_labels),
    url(r'^export_labels_form', stratosource.user.views.export_labels_form),
    url(r'^release_create_package/(.+)$', stratosource.user.views.create_release_package),
    url(r'^release_package/(.+)$', stratosource.user.views.release_package),
    url(r'^release_delete_package/(.+)$', stratosource.user.views.delete_release_package),
    url(r'^release_push_package/(.+)$', stratosource.user.views.push_release_package),
    url(r'^release_push_status/(.+)$', stratosource.user.views.release_push_status),
    url(r'^releases', stratosource.user.views.releases),
    url(r'^release/(.+)$', stratosource.user.views.release),
    url(r'^unreleased/(.+)/(.+)$', stratosource.user.views.unreleased),
    url(r'^object/(\d+)$', stratosource.user.views.object),
    url(r'^stories', stratosource.user.views.stories),
    url(r'^instory/(\d+)$', stratosource.user.views.instory),
    url(r'^search', stratosource.user.views.search),
    url(r'^ajax/releases', stratosource.user.ajax.releases),
    url(r'^ajax/createrelease', stratosource.user.ajax.createrelease),
    url(r'^ajax/deleterelease', stratosource.user.ajax.deleterelease),
    url(r'^ajax/markreleased', stratosource.user.ajax.markreleased),
    url(r'^ajax/getstories', stratosource.user.ajax.getstories),
    url(r'^ajax/getsprints', stratosource.user.ajax.getsprints),
    url(r'^ajax/addtostory', stratosource.user.ajax.addtostory),
    url(r'^ajax/updaterelease', stratosource.user.ajax.updaterelease),
    url(r'^ajax/ignoreitem/(\d+)$', stratosource.user.ajax.ignoreitem),
    url(r'^ajax/ignoreselected', stratosource.user.ajax.ignoreselected),
    url(r'^ajax/ignoretranslation/(\d+)$', stratosource.user.ajax.ignoretranslation),
    url(r'^ajax/addreleasetask', stratosource.user.ajax.add_release_task),
    url(r'^ajax/editreleasetask', stratosource.user.ajax.edit_release_task),
    url(r'^ajax/delreleasetask',stratosource.user.ajax.delete_release_task),
    url(r'^ajax/reorderreleasetasks', stratosource.user.ajax.reorder_release_tasks),
    url(r'^ajax/releasetasks/(.)(\d+)$', stratosource.user.ajax.get_release_tasks),

    url(r'^repos/', stratosource.admin.views.repos),
    url(r'^branches/(\d+)$', stratosource.admin.views.branches),
    url(r'^commits/(\d+)$', stratosource.admin.views.commits),
    url(r'^commit/(\d+)$', stratosource.admin.views.commit),

    #(r'^csmedia/(?P<path>.*)$', 'django.views.static.serve',
    #    {'document_root': os.path.join(PROJECT_PATH, 'csmedia')}),

    # admin menu support
    url(r'^admin/', stratosource.user.admin_views.adminMenu),
    url(r'^lastlog/(\d+)/(.*)$', stratosource.user.admin_views.last_log),
    url(r'^newbranch/', stratosource.user.admin_views.newbranch),
    url(r'^editbranch/(\d+)$', stratosource.user.admin_views.editbranch),
    url(r'^editbranchdetails/(\d+)$', stratosource.user.admin_views.edit_branch_details),
    url(r'^repo_admin_form_action', stratosource.user.admin_views.repo_form_action),
    url(r'^branch_admin_form_action', stratosource.user.admin_views.branch_form_action),
    url(r'^newrepo/', stratosource.user.admin_views.newrepo),
    url(r'^editrepo/(\d+)$', stratosource.user.admin_views.editrepo),
    url(r'^repo_form_action',stratosource.user.admin_views.repo_form_action),
]
