"""ss3 URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
#from django.contrib import admin
from django.urls import path
import os

import stratosource.user.views
import stratosource.user.ajax
import stratosource.user.unit_testing_views
import stratosource.admin.views
import stratosource.user.admin_views
import stratosource.user.setup_views

urlpatterns = [
#    path('admin/', admin.site.urls),

    path('', stratosource.user.views.home, name='home'),
    path('setup/<stage>/', stratosource.user.setup_views.setup),
    path('configs/', stratosource.user.views.configs),
    path('unit_testing_results/', stratosource.user.unit_testing_views.results),
    path('unit_testing_result/<run_id>', stratosource.user.unit_testing_views.result),
    path('ajax/unit_testing_result_list/<id>/', stratosource.user.unit_testing_views.ajax_unit_test_resultslist),
    path('unit_testing_admin/', stratosource.user.unit_testing_views.admin),
    path('unit_test_schedule_admin_form_action', stratosource.user.unit_testing_views.unit_test_schedule_admin_form_action),
    path('new_test_schedule/', stratosource.user.unit_testing_views.new_test_schedule),
    path('edit_test_schedule/<id>/', stratosource.user.unit_testing_views.edit_test_schedule),
    path('rally_projects/', stratosource.user.views.rally_projects),
    path('manifest/<release_id>', stratosource.user.views.manifest),
    path('export_labels_form', stratosource.user.views.export_labels_form),
    path('release_create_package/', stratosource.user.views.create_release_package),
    path('release_package/<id>', stratosource.user.views.release_package),
    path('deployment', stratosource.user.views.deployment_dashboard),
    path('release_delete_package/<id>', stratosource.user.views.delete_release_package),
    path('release_push_package/<id>', stratosource.user.views.push_release_package),
    path('releases', stratosource.user.views.releases),
    path('release/<id>', stratosource.user.views.release),
    path('unreleased/<repo_name>/<branch_name>/', stratosource.user.views.unreleased),
    path('object/<object_id>', stratosource.user.views.object),
    path('stories', stratosource.user.views.stories),
    path('instory/<story_id>', stratosource.user.views.instory),
    path('search', stratosource.user.views.search),
    path('ajax/releases', stratosource.user.ajax.releases),
    path('ajax/createrelease', stratosource.user.ajax.createrelease),
    path('ajax/deleterelease', stratosource.user.ajax.deleterelease),
    path('ajax/markreleased', stratosource.user.ajax.markreleased),
    path('ajax/getstories', stratosource.user.ajax.getstories),
    path('ajax/getsprints', stratosource.user.ajax.getsprints),
    path('ajax/addtostory', stratosource.user.ajax.addtostory),
    path('ajax/updaterelease', stratosource.user.ajax.updaterelease),
    path('ajax/ignoreitem/<id>', stratosource.user.ajax.ignoreitem),
    path('ajax/ignoreselected', stratosource.user.ajax.ignoreselected),
    path('ajax/ignoretranslation/<id>', stratosource.user.ajax.ignoretranslation),
    path('ajax/addreleasetask', stratosource.user.ajax.add_release_task),
    path('ajax/editreleasetask', stratosource.user.ajax.edit_release_task),
    path('ajax/delreleasetask',stratosource.user.ajax.delete_release_task),
    path('ajax/reorderreleasetasks', stratosource.user.ajax.reorder_release_tasks),
    #path('ajax/releasetasks/<type>/<id>', stratosource.user.ajax.get_release_tasks),

    path('repos/', stratosource.admin.views.repos),
    path('branches/<repo_id>', stratosource.admin.views.branches),
    path('commits/<branch_id>', stratosource.admin.views.commits),
    path('commit/<commit_id>', stratosource.admin.views.commit),

    # admin menu support
    path('admin/', stratosource.user.admin_views.adminMenu),
    path('lastlog/<branch_id>/<logtype>', stratosource.user.admin_views.last_log),
    path('newbranch/', stratosource.user.admin_views.newbranch),
    path('editbranch/<branch_id>', stratosource.user.admin_views.editbranch),
    path('editbranchdetails/<branch_id>', stratosource.user.admin_views.edit_branch_details),
    path('repo_admin_form_action', stratosource.user.admin_views.repo_form_action),
    path('branch_admin_form_action', stratosource.user.admin_views.branch_form_action),
    path('newrepo/', stratosource.user.admin_views.newrepo),
    path('editrepo/<repo_id>', stratosource.user.admin_views.editrepo),
    path('repo_form_action',stratosource.user.admin_views.repo_form_action),
]
