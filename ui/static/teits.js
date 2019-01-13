var DISPLAY_COUNT_TIMER = 1000
var DISPLAY_SPEED_TIMER = 1000
var DISPLAY_BATTERY_TIMER = 5000
var PATROL_TIMER = 5000




patrol_in_progess = false;

$(function(){
    $('.drag').draggable({revert:"invalid",revertDuration: 300}); // appel du plugin
});

function set_drone_position(drone_id,drop_zone,action){
    $.ajax({
            url: 'set_drone_position',
            type: 'post',
            data: {"drone_id":drone_id,"drop_zone":drop_zone,"action":action},
            success:function(data){
                console.log(data)
            }
        });
}



function set_zone_position(zone_id,top,left){
    $.ajax({
            url: 'set_zone_position',
            type: 'post',
            data: {"zone_id":zone_id,"top":top,"left":left},
            success:function(data){
                console.log(data)
            }
        });
}

function update_zone_coordinates(zone_id){
    $.ajax({
            url: 'get_zone_coordinates',
            type: 'post',
            data: {"zone_id":zone_id},
            success:function(data){
                coordinates = JSON.parse(data);
                console.log(coordinates)
                $("#zone_x").val(coordinates.x);
                $("#zone_y").val(coordinates.y);
            }
        });
}


$('.drop.zone').droppable({
    drop : function(e,ui){
        var drop_zone = $(this).attr('id');
        var drone_id = ui.draggable.attr('id');
        set_drone_position(drone_id,drop_zone);       
    },
}); 

$('.drop.zone').click(function(e){
    $('#drone_1').animate({
            top : e.pageY - 44,
            left: e.pageX - 35
            }, 2000, function() {
                var drop_zone = e.target.id;
                var drone_id = "drone_1";
                set_drone_position(drone_id,drop_zone);  
            });
});


$('#main_map.drop').droppable({
    drop : function(e,ui){
        var zone_id = ui.draggable.attr('id');
        var top = ui.draggable.offset().top / ui.draggable.parent().height() * 100;
        var left = ui.draggable.offset().left / ui.draggable.parent().width() * 100;
        console.log(top);
        console.log(left);
        set_zone_position(zone_id,top,left); 
    },
}); 



function move_to_position(drone_id,zone_id,action){
    console.log("moving " + drone_id + " to " + zone_id);
    // Define zone center
    var zone_div = $("#"+ zone_id);
    var drone_div = $('#' + drone_id);
    var position = zone_div.position();
    var height = zone_div.height();
    var width = zone_div.width();
    set_drone_position(drone_id,zone_id,action);
    drone_div.animate({
        top : position.top + height/2 - drone_div.height()/2,
        left: position.left + width/2 - drone_div.width()/2
        }, 2000);
    }

$("#back_home_button").click(function(){
    $(".drone").each(function(){
        console.log("Stop patrolling");
        patrol_in_progess = false;
        console.log($(this).css('display'));
        if($(this).css('display')!='none'){move_to_position($(this).attr("id"),"home_base","land");}
    })
})

$("#new_drone_button").click(function(){
        if (!$("#drone_1_ui").is(":visible")){
            $("#drone_1").show()
            $("#drone_1_ui").show();
            set_drone_position("drone_1","home_base","takeoff");

        }
        else if (!$("#drone_2_ui").is(":visible")){
            $("#drone_2").show()
            $("#drone_2_ui").show();
            set_drone_position("drone_2","home_base","takeoff");
        }
        else {
            $("#drone_3").show()
            $("#drone_3_ui").show();
            set_drone_position("drone_3","home_base","takeoff");

        }
})


$("#patrol_button").click(function(){
    console.log("Start patroling");
    patrol_in_progess = true;
    patrol();
})




function move_to_next_waypoint(drone_id){
    $.ajax({
        url: 'get_next_waypoint',
        type: 'post',
        data: {"drone_id":drone_id},
        success:function(data){
            console.log("next waypoint for " + drone_id);
            console.log(data);
            var next_waypoint = data;
            move_to_position(drone_id, next_waypoint);
        }
    });
}

function patrol(){
    console.log("Patroling");
    $(".drone").each(function(){
        var drone_id = $(this).attr("id")
        if(patrol_in_progess && $(this).css('display')!='none'){
            move_to_next_waypoint(drone_id);
        }
    })
    if(patrol_in_progess){
        setTimeout(function(){
                    patrol();
                  }, PATROL_TIMER);
    }
}


$("#zone_save").click(function(){
        $.ajax({
            url: 'save_zone',
            type: 'post',
            data: {"zone_name":$("#zone_name").val(),
                    "zone_width":$("#zone_width").val(),
                    "zone_height":$("#zone_height").val(),
                    "zone_top":$("#zone_top").val(),
                    "zone_left":$("#zone_left").val(),
                    "zone_x":$("#zone_x").val(),
                    "zone_y":$("#zone_y").val(),
                    },
            success:function(data){
                console.log(data);
                location.reload();
            }
        });
})


$("#zone_delete").click(function(){
        $.ajax({
            url: 'delete_zone',
            type: 'post',
            data: {"zone_name":$("#zone_name").val()
                    },
            success:function(data){
                console.log(data);
                location.reload();
            }
        });
})


function update_zone_info(zone_id){
    var zone_div = $("#"+zone_id);
    $("#zone_name").val(zone_div.attr("id"));
    $("#zone_height").val(Math.round(zone_div.height()/zone_div.parent().height()*100));
    $("#zone_width").val(Math.round(zone_div.width()/zone_div.parent().width()*100));
    $("#zone_top").val(Math.round(zone_div.offset().top/zone_div.parent().height()*100));
    $("#zone_left").val(Math.round(zone_div.offset().left/zone_div.parent().width()*100));
}

$(".zone.drag").click(function(){
    console.log("update");
    var zone_id = $(this).attr("id")
    update_zone_info(zone_id);
    update_zone_coordinates(zone_id);
})

$( document ).ready(function() {
    var hb = $("#home_base");
    var hb_top = hb.offset().top;
    var hb_left = hb.offset().left;
    var hb_height = hb.height();
    var hb_width = hb.width();
    $(".drone").each(function(){
        $(this).css({top: hb_top + hb_height/2 - $(this).height()/2,
                     left: hb_left + hb_width/2 - $(this).width()/2,
                     position: 'absolute'});
        });
    $(".drone_ui").each(function(){if($(this).attr("id") != "drone_1_ui"){$(this).hide();}});
    $(".drone").each(function(){$(this).hide();});
    update_battery();
    update_speed();
    update_count();
});

function update_battery(){
    $(".drone_info").each(function(){
        var drone_info_div = $(this);
        $.ajax({
            url: 'get_battery_pct',
            type: 'post',
            data: {"drone_id":drone_info_div.attr("drone_id")},
            success:function(data){
                drone_info_div.children(".battery_pct").text(data+"%");
                set_battery(drone_info_div.children(".battery_pct"));
            }
        });
    });
    setTimeout(function(){
            update_battery();
          }, DISPLAY_BATTERY_TIMER);

}

function update_speed(){
    $(".drone_info").each(function(){
        var drone_info_div = $(this);
        $.ajax({
            url: 'get_speed',
            type: 'post',
            data: {"drone_id":drone_info_div.attr("drone_id")},
            success:function(data){
                drone_info_div.children(".speed").text(data);
            }
        });
    });
    setTimeout(function(){
            update_speed();
          }, DISPLAY_SPEED_TIMER);

}


function update_count(){
    $(".drone_info").each(function(){
        var drone_info_div = $(this);
        $.ajax({
            url: 'get_count',
            type: 'post',
            data: {"drone_id":drone_info_div.attr("drone_id")},
            success:function(data){
                drone_info_div.children(".count").text(data);
            }
        });
    });
    setTimeout(function(){
            update_count();
          }, DISPLAY_COUNT_TIMER);

}


function update_log_data(){
    $(".drone_info").each(function(){
        $.ajax({
            url: 'get_log_data',
            type: 'post',
            data: {"drone_id":$(this).attr("drone_id")},
            success:function(data){
                $(this).children(".log_data").text(data);
            }
        });
    });

    setTimeout(function(){
            update_log_data();
          }, 100);
}



function set_battery(element){
    var battery_pct = parseInt(element.text().slice(0,-1));
    
    if(battery_pct > 75){
        element.parent().children(".battery_gauge").css("background-image", "url(/static/battery_100.png)");
    } 
    else if(battery_pct > 50){
        element.parent().children(".battery_gauge").css("background-image", "url(/static/battery_75.png)");
    } 
    else if(battery_pct > 25){
        element.parent().children(".battery_gauge").css("background-image", "url(/static/battery_50.png)");
    } 
    else if(battery_pct > 15){
        element.parent().children(".battery_gauge").css("background-image", "url(/static/battery_25.png)");
    }
    else {
        element.parent().children(".battery_gauge").css("background-image", "url(/static/battery_15.png)");
    }
}