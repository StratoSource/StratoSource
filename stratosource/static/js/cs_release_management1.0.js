///////////////////////////////////////////
// Task Related
///////////////////////////////////////////

editingTask = '';
lastValue = '';

function refreshTasks() {
    reltype = 'r';
    id = release_id;
    if (id == null){
        id = story_id;
        reltype = 's';
    }
    if (cancelEdit()){
        jQuery('#taskList').load('/ajax/releasetasks/' + reltype + '/' + id);
        editingTask = '';
        lastValue = '';
    }
}

function loadTaskListReadOnly(){
    jQuery('#taskList').load('/ajax/releasetasks/r/' + release_id + '?readonly=true');
}

function addTask(){
    task = jQuery('#taskName').val();
    if (task != null && task != ''){
        jQuery.ajax({
          url: "/ajax/addreleasetask/?rel_id=" + release_id + '&story_id=' + story_id + "&task=" + escape(task),
          success: function(data){
            if (!data.success){
                alert('ERROR: ' + data.error);
            } else {
                refreshTasks();
                jQuery('#taskName').val('');
            }
          }
        });
    }
    
}

function flagTask(release_id, id, is_checked, branch_id){
    jQuery.ajax({
        url: "/ajax/editreleasetask/?rel_id=" + release_id + "&task_id=" + id + '&done=' + is_checked + '&branch_id=' + branch_id,
        success: function(data){
            if (!data.success){
                alert('ERROR: ' + data.error);
            }
        }
    });
    
}

function deleteTask(id){
    if (confirm('Are you sure?')){
        jQuery.ajax({
            url: "/ajax/delreleasetask/?rel_id=" + release_id + "&task_id=" + id,
            success: function(data){
                if (!data.success){
                    alert('ERROR: ' + data.error);
                } else {
                    refreshTasks();
                }
            }
        });
    }            
}

function editTask(id){
    if (editingTask == id)
        return;

    if (!cancelEdit()){
        return;
    }
    
    editingTask = id;
    curVal = jQuery('#' + id + 'Name').html();
    lastValue = curVal;
    jQuery('#' + id + 'Name').html('<textarea id="taskName' + id + '" name="taskName' + id + '" cols="100" rows="2">' + curVal + '</textarea>');
    if (!jQuery('#save' + id).is(":visible")){
        jQuery('#save' + id).css('display','inline');
        jQuery('#cancel' + id).css('display','inline');
        jQuery('#delete' + id).toggle();        
        jQuery('#edit' + id).toggle();
    }
}

function cancelEdit(){
    if (editingTask == ''){
        return true;
    } else {
        if (!confirm('Are you sure? You will lose changes on the current item you are editing.')){
            return false;
        }
    }
    
    id = editingTask;
    jQuery('#' + id + 'Name').html(lastValue);
    if (jQuery('#save' + id).is(":visible")){
        jQuery('#save' + id).css('display','none');
        jQuery('#cancel' + id).css('display','none');
        jQuery('#delete' + id).toggle();        
        jQuery('#edit' + id).toggle();
    }
    editingTask = '';
    lastValue = '';
    
    return true;
}

function saveTask(id, branch_id){
    newVal = jQuery('#taskName' + id).val();
    jQuery.ajax({
        url: "/ajax/editreleasetask/?rel_id=" + release_id + "&task_id=" + id + '&newVal=' + escape(newVal) + '&branch_id=' + branch_id,
        success: function(data){
            if (!data.success){
                alert('ERROR: ' + data.error);
            } else {
                editingTask = '';
                lastValue = '';
                refreshTasks();
            }
        }
    });    
}

function updateTaskUser(release_id, id, user_id, branch_id){
    jQuery.ajax({
        url: "/ajax/editreleasetask/?rel_id=" + release_id + "&task_id=" + id + '&branch_id=' + branch_id + '&user_id=' + user_id,
        success: function(data){
            if (!data.success){
                alert('ERROR: ' + data.error);
            }
        }
    });
    
}

function updateTaskType(release_id, id, type_id, branch_id){
    jQuery.ajax({
        url: "/ajax/editreleasetask/?rel_id=" + release_id + "&task_id=" + id + '&branch_id=' + branch_id + '&type_id=' + type_id,
        success: function(data){
            if (!data.success){
                alert('ERROR: ' + data.error);
            }
        }
    });
    
}

function enableSorting(){
    jQuery("#sortable tbody").sortable({
        helper: fixHelper,
        update: updateHelper,
        disabled: false
    });
    jQuery("#sortUnlockButton").hide();
    jQuery("#sortLockButton").show();
}

function disableSorting(){
    jQuery("#sortable tbody").sortable({ disabled: true });
    jQuery("#sortUnlockButton").show();
    jQuery("#sortLockButton").hide();
}


// Return a helper with preserved width of cells
var fixHelper = function(e, ui) {
    ui.children().each(function() {
        jQuery(this).width($(this).width());
    });
    return ui;
};
 
var updateHelper = function(e, ui) {
    orderList = jQuery("#sortable tbody").sortable( "toArray" );
    jQuery.ajax({
        url: "/ajax/reorderreleasetasks/?order=" + orderList,
        success: function(data){
            if (!data.success){
                alert('ERROR: ' + data.error);
            } else {
                refreshTasks();
            }
        }
    });
};
