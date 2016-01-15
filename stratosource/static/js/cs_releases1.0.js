/* 
 * To change this template, choose Tools | Templates
 * and open the template in the editor.
 */

function newRelease(branch) {
     $("#createRelease" + branch).show();
     $("#createReleaseLink" + branch).hide();
     if ($("#" + branch + "releasesListE"))
        $("#" + branch + "releasesListE").hide();
}

function refreshReleases(){
    $.ajax({
      url: "/ajax/releases",
      cache: false,
      success: function(html){
         var rows = $("tr");
         for(var i = 0; i < rows.length; i++){
            if (rows[i].id.match('^releasesList')){
                $("#" + rows[i].id).remove();
            }
         }
         $("#headers").after(html);
      }
    });
}

function cancelCreate(branch){
    $("#createRelease" + branch).hide();
    $("#createReleaseLink" + branch).show();
    $( "#estRelDate" + branch ).val('');
    $( "#relName" + branch ).val('');
    if ($("#" + branch + "releasesListE"))
        $("#" + branch + "releasesListE").show();
}

function createRelease(branch){
    $.ajax({
      url: "/ajax/createrelease",
      cache: false,
      data: "branch=" + encodeURI(branch) + "&name=" + encodeURI($( "#relName" + branch ).val()) + "&estRelDate=" +  $( "#estRelDate" + branch ).val(),
      success: function(data){
          if (!data.success){
               alert(data.error)
          } else {
               refreshReleases();
               $("#createRelease" + branch).hide();
               $("#createReleaseLink" + branch).show();
               $( "#estRelDate" + branch ).val('');
               $( "#relName" + branch ).val('');
          }
      }
    });
}

function deleteRelease(id, name, branch){
    if (confirm("Are you sure you want to delete '" + name + "'?")){
        $.ajax({
          url: "/ajax/deleterelease",
          cache: false,
          data: "id=" + id + "&branch=" + branch,
          success: function(html){
            refreshReleases();
          }
        });
        }
}

function markReleased(id, name, branch, refreshPage){
    if (confirm("Are you sure you want to mark '" + name + "' released? This cannot be undone!")){
        $.ajax({
          url: "/ajax/markreleased",
          cache: false,
          data: "id=" + id,
          success: function(json){
            if (json.success && !refreshPage){
                refreshReleases();
            } if (json.success && refreshPage) {
                location.reload();
            } else {
                alert(json.error);
            }
          }
        });
        }
}

function updateRelease(releaseId, date, name, branch){
     dataStr = "id=" + releaseId;
     if (date != null){
          dataStr += "&date=" + encodeURI(date);
     }
     if (name != null){
          dataStr += "&name=" + escape(name);
     }
    $.ajax({
      url: "/ajax/updaterelease",
      cache: false,
      data: dataStr,
      success: function(json){
          if(json.success){
              refreshReleases();
               editingRel = '';
          } else {
              alert(json.error);
          }
      }
    });
}

function editReleaseStart(releaseId){
     if (editingRel != ''){
          alert('Please finish editing the other release first');
          return;
     }
     editingRel = releaseId;
     calChanged = false;
     jQuery("#save" + releaseId).show();
     jQuery("#cancel" + releaseId).show();
     jQuery("#edit" + releaseId).hide();
     jQuery("#relNameRO" + releaseId).hide();
     jQuery("#relName" + releaseId).show()
     jQuery("#relDateRO" + releaseId).hide();
     jQuery("#relDate" + releaseId).show();
}

function cancelRelease(){
     refreshReleases();
     editingRel = '';
}

function saveRelease(releaseId, branch){
     updateRelease(releaseId, jQuery('#estRelDate' + releaseId).val(), jQuery('#txtRelName' + releaseId).val(), branch);     
}


// Watching it see if the calendar was changed
var calChanged = false;
var editingRel = '';

