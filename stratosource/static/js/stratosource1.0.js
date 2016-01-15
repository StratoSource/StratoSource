/* 
 * To change this template, choose Tools | Templates
 * and open the template in the editor.
 */
var openSections = {};

$(document).ready(function() {
    var h = document.location.hash;
    if (h.length > 1){
        var sections = getSections();
        for (i in sections){
            jQuery('#' + sections[i]).show();
            if (sections[i].indexOf('min') > -1){
                jQuery('#max' + sections[i].substring(3,sections[i].length)).hide();
            }
            openSections[sections[i]] = '1';
        }
    }
});

function getSections(){
    var h = document.location.hash;
    return h.substring(1,h.length - 1).split(',');
}

function toggle(objectId){
    jQuery('#' + objectId).toggle();
    if (jQuery('#' + objectId).is(":visible") ){
        openSections[objectId] = '1';
    } else {
        delete openSections[objectId];
    }
    serializeOpenSections();
}

function serializeOpenSections(){
    var s = '';
    for (var key in openSections){
        s += key + ',';
    }
    document.location.hash = s;
}