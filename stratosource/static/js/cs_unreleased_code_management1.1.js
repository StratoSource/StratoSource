/* 
 * To change this template, choose Tools | Templates
 * and open the template in the editor.
 */

function flagAll(checked){
    var checkboxes = $("input");
    for(var i = 0; i < checkboxes.length; i++){
        if (checkboxes[i].name == 'chkItem' || checkboxes[i].id == 'chkAll' || checkboxes[i].name == 'chkTrans'){
            checkboxes[i].checked = checked;
        }
    }
}

function selectSection(name, isSelect){
    selectMatching(name + '/', false, isSelect);
}

function ignoreItem(id, ok){
    $.ajax({
      url: "/ajax/ignoreitem/" + id,
      data: "ok=" + ok,
      cache: false,
      success: function(json){
          if(json.success){
              document.location.reload();
          } else {
              alert(json.error);
          }
      }
    });
}


function ignoreTranslation(id, ok){
    $.ajax({
      url: "/ajax/ignoretranslation/" + id,
      data: "ok=" + ok,
      cache: false,
      success: function(json){
          if(json.success){
              document.location.reload();
          } else {
              alert(json.error);
          }
      }
    });
}

function ignoreSelected(){
    $('#ignoreSelected').html('<img height="10px" src="/csmedia/images/line_throbber.gif" alt="Loading..."/>');
    $('#ignoreSelectedBottom').html('<img height="10px" src="/csmedia/images/line_throbber.gif" alt="Loading..."/>');

    var query = 'releaseid=' + $("#release").val();
    var checkboxes = $("input");

    for(var i = 0; i < checkboxes.length; i++){
        if (checkboxes[i].name == 'chkItem' && (checkboxes[i].checked)){
            query += '&ii=' + checkboxes[i].id;
        } else if (checkboxes[i].name == 'chkTrans' && (checkboxes[i].checked)){
            query += '&ti=' + checkboxes[i].id;
        }
    }

    $.ajax({
      url: "/ajax/ignoreselected",
      data: query,
      cache: false,
      success: function(json){
          if(json.success){
              flagAll(false);
              document.location.reload();
          } else {
              alert(json.error);
          }
      }
    });
}

function promptStoryAdd(){
    $('#sprintId').html('');
    $.ajax({
      url: "/ajax/getsprints",
      cache: false,
      success: function(json){
          if(json.success){
            for (var i = 0; i < json.sprints.length; i++){
                $('#sprintId').
                    append($("<option></option>").
                    attr("value",json.sprints[i]).
                    text(json.sprints[i]));
            }                    
          } else {
              alert(json.error);
          }
      }
    });

    var count = 0;
    var checkboxes = $("input");
    var itemList = '<br/><div><strong>Included Items:</strong></div><br/><ul>';
    for(var i = 0; i < checkboxes.length; i++){
        if ((checkboxes[i].name == 'chkTrans' || checkboxes[i].name == 'chkItem') && (checkboxes[i].checked)){
            itemList += "<li>" + checkboxes[i].value + "</li>";
            count++;
        }
    }

    if (count == 0){
        alert('Please select at least one item to add');
        return;
    }

    itemList += "</ul>";
    $("#itemList").html(itemList);
    $("#storyManager" ).dialog(
    {
        buttons:
        {
            "Cancel": function()
             {
                 $(this).dialog("close");
             },
            "Associate to Story": function()
             { 
                var query = 'releaseid=' + $("#release").val()
                    + "&storyId=" + $("#storyId").val()
                    + "&storyName=" + encodeURI($("#storyName").val())
                    + "&storyRallyId=" + encodeURI($("#storyRallyId").val())
                    + "&storyURL=" + encodeURI($("#storyURL").val());

                for(var i = 0; i < checkboxes.length; i++){
                    if (checkboxes[i].name == 'chkItem' && (checkboxes[i].checked)){
                        query += '&itemid=' + checkboxes[i].id;
                    } else if (checkboxes[i].name == 'chkTrans' && (checkboxes[i].checked)){
                        query += '&transid=' + checkboxes[i].id;
                    }
                }
                addToStory(query, this);
             }
         }, 
         modal: true,
         minWidth: 700,
         maxWidth: 1100,
         maxHeight: 600,
         minHeight: 400,
         height: 500
     });
}

function loadStories(){   
    $("#storyId").html('');
    sprint = $("#sprintId option:selected").text();
    if (sprint != '' && sprint != 'None'){
        if (sprint != '' && sprint.length > 0){
            sprint = "sprintName=" + sprint;
        }
        $.ajax({
          url: "/ajax/getstories",
          cache: false,
          data: sprint,
          success: function(json){
              if(json.success){
                for (var i = 0; i < json.stories.length; i++){
                    story = json.stories[i];
                    storyName = story.substring(0,story.lastIndexOf('|'));
                    storyId = story.substring(story.lastIndexOf('|') + 1,story.length);
                    $('#storyId').
                        append($("<option></option>").
                        attr("value",storyId).
                        text(storyName));
                }                    
              } else {
                  alert(json.error);
              }
          }
        });
    }
}

function addToStory(query, modal){
    $(modal).dialog( "disable" );
    $.ajax({
      url: "/ajax/addtostory",
      data: query,
      cache: false,
      success: function(json){
          if(json.success){
              flagAll(false);
              document.location.reload();
          } else {
              alert(json.error);
          }
      }
    });
}

function selectFiltered(){
    var filter = $("#filter").val();
    selectMatching(filter, false, true);
}

function refreshFilters(){
    var search = $("#txtSearch").val();
    var username = $("#cboUserName").val();
    var endDate = $("#endDate").val();
    var startDate = $("#startDate").val();
    var type = $("#cboType").val();
    document.location = '?go=true&search=' + escape(search) + '&username=' + escape(username) + '&startDate=' + startDate + '&endDate=' + endDate + '&type=' + type + document.location.hash;
}

function selectMatching(filter, uncheckNonMatch, isSelect){
    var checkboxes = $("input");
    if (filter == ""){
        $("#chkAll").attr('checked', true);
    } else {
        if (uncheckNonMatch){
            $("#chkAll").attr('checked', false);
        }
    }
    for(var i = 0; i < checkboxes.length; i++){
        if (checkboxes[i].name == 'chkItem' || checkboxes[i].name == 'chkTrans'){
            if (checkboxes[i].value.match(filter)){
                // If it maches, change it
                checkboxes[i].checked = isSelect;
            }
        }
    }
}

$(window).load(function() {
    $( "#startDate" ).datepicker();
    $( "#endDate" ).datepicker();
    $("#sprintId").change(function () {
        loadStories();
    })
    .trigger('change');
    
    $('#filter').bind('keypress', function(e) {
        if(e.keyCode==13){
            selectFiltered();
    }
    
    $('#txtSearch').bind('keypress', function(e) {
        if(e.keyCode==13){
            refreshFilters();
    }
})
})
});
