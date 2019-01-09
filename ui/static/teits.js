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
            url: 'update_zone_position',
            type: 'post',
            data: {"zone_id":zone_id,"top":top,"left":left},
            success:function(data){
                console.log(data)
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
            }, 1000, function() {
                var drop_zone = e.target.id;
                var drone_id = "drone_1";
                set_drone_position(drone_id,drop_zone);  
            });
});


$('#main_map.drop').droppable({
    drop : function(e,ui){
        var zone_id = ui.draggable.attr('id');
        var top = ui.draggable.offset().top;
        var left = ui.draggable.offset().left;
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
        }, 1000);
    }

$("#back_home_button").click(function(){
    $(".drone").each(function(){
        patrol_in_progess = false;
        move_to_position($(this).attr("id"),"home_base","land")
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
    $(".drone").each(function(){
        var drone_id = $(this).attr("id")
        if(patrol_in_progess){
            move_to_next_waypoint(drone_id);
        }
    })
    setTimeout(function(){
                patrol();
              }, 3000);
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

$("#set_scene_width_button").click(function(){
        $.ajax({
            url: 'set_scene_width',
            type: 'post',
            data: {"scene_width":$("#scene_width").val()
                    },
            success:function(data){
                console.log(data);
                location.reload();
            }
        });
})


function update_zone_info(zone_id){
    $("#zone_name").val($("#"+zone_id).attr("id"));
    $("#zone_width").val($("#"+zone_id).width());
    $("#zone_height").val($("#"+zone_id).height());
    $("#zone_top").val($("#"+zone_id).offset().top);
    $("#zone_left").val($("#"+zone_id).offset().left);
}

$(".zone.drag").click(function(){
    console.log("update");
    update_zone_info($(this).attr("id"));
})

$( document ).ready(function(){
/*  display_streams();
  display_countries();
  update_country_charts();*/
});





var active_streams = [];
var deployed_countries = [];


function contains(array,string){
    var in_array = false; 
    for (var i=0;i<array.length;i++){
        if (array[i]==string){
            in_array = true;
            break;
        }
    }
    return in_array;
}


$('#recycle').droppable({
  drop : function(e,ui){
        var zone = ui.draggable.attr('id').split("_")[0];
        $("#"+zone+"_docker_image").hide();
        $.ajax({
              url: 'remove_country',
              type: 'post',
              data: {"country":zone},
              success:function(data){
                console.log(zone + " container stopped")
                $("#"+zone+"_chart").remove();
              }
          });
    }
}); // ce bloc servira de zone de dépôt




function display_streams(){
    $.ajax({
        url: 'get_active_streams',
        type: 'get',
        success:function(data){
            var current_streams = JSON.parse(data);
            console.log(current_streams);
            // Iterate over object
            $.each(current_streams,function(index,value){
                // get chart
                if (contains(active_streams,value)){
                  $("#" + value + "_streams").show();
                }
            });
            $.each(active_streams,function(index,value){
                // get chart
                if (!contains(current_streams,value)){
                  $("#" + value + "_streams").hide();
                }
            });
            active_streams = current_streams;
            if (active_streams.length>0){
              $("#replicate_streams").show();
            }else{
              $("#replicate_streams").hide();
              $("#global_streams").hide();
            }
            setTimeout(function(){
                display_streams();
              }, 1000);
        }
    });
}

