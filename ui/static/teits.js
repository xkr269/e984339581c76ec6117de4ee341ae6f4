var DISPLAY_COUNT_TIMER = 1000
var DISPLAY_SPEED_TIMER = 1000
var DISPLAY_CONNECTION_STATUS_TIMER = 1000
var DISPLAY_BATTERY_TIMER = 5000
var PATROL_TIMER = 3000
var GRAPH_TIMER = 2000 
var graph_color = "#6CFC5F"



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
            $("#drone_1_video").setAttr("src","video_stream/drone_1");
            draw_chart("drone_1_count_graph","drone_1_count");
            set_drone_position("drone_1","home_base","takeoff");

        }
        else if (!$("#drone_2_ui").is(":visible")){
            $("#drone_2").show()
            $("#drone_2_ui").show();
            $("#drone_2_video").setAttr("src","video_stream/drone_2");
            draw_chart("drone_2_count_graph","drone_2_count");
            set_drone_position("drone_2","home_base","takeoff");
        }
        else {
            $("#drone_3").show()
            $("#drone_3_ui").show();
            $("#drone_3_video").setAttr("src","video_stream/drone_3");
            draw_chart("drone_3_count_graph","drone_3_count");
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
    update_global_count();
    update_connection_status(); 
    draw_chart("global_count_graph","global_count");
});

function update_battery(){
    $(".drone_ui").each(function(){
        var div = $(this);
        $.ajax({
            url: 'get_battery_pct',
            type: 'post',
            data: {"drone_id":div.attr("drone_id")},
            success:function(data){
                div.children(".battery_pct").text(data+"%");
                set_battery(div.children(".battery_pct"));
            }
        });
    });
    setTimeout(function(){
            update_battery();
          }, DISPLAY_BATTERY_TIMER);

}

function update_speed(){
    $(".drone_ui").each(function(){
        var div = $(this);
        $.ajax({
            url: 'get_speed',
            type: 'post',
            data: {"drone_id":div.attr("drone_id")},
            success:function(data){
                div.children(".speed").text(data);
            }
        });
    });
    setTimeout(function(){
            update_speed();
          }, DISPLAY_SPEED_TIMER);

}

function update_global_count(){
    var count = 0;
    $(".count").each(function(){
        var div = $(this);
        if(div.is(":visible")){
            count = count + Number(div.text());
            console.log(count);
        }
    });
    $("#global_count").text(count);
    setTimeout(function(){
        update_global_count();
    }, DISPLAY_COUNT_TIMER);
}

function update_count(){
    $(".count").each(function(){
        var div = $(this);
        if(div.is(":visible")){
            $.ajax({
                url: 'get_count',
                type: 'post',
                data: {"drone_id":div.parent().attr("drone_id")},
                success:function(data){
                    div.text(data);
                }
            });
        }
    });
    setTimeout(function(){
            update_count();
          }, DISPLAY_COUNT_TIMER);

}

function update_connection_status(){
    $(".drone_ui").each(function(){
        var div = $(this);
        $.ajax({
            url: 'get_connection_status',
            type: 'post',
            data: {"drone_id":div.attr("drone_id")},
            success:function(data){
                div.children(".connection_status").text(data);
                if(data == "connected"){
                    div.children(".connection_status").removeClass("disconnected");
                    div.children(".connection_status_video").removeClass("disconnected");
                    div.children(".connection_status").addClass("connected");
                    div.children(".connection_status_video").text("");

                }else{
                    div.children(".connection_status").removeClass("connected");
                    div.children(".connection_status").addClass("disconnected");
                    div.children(".connection_status_video").addClass("disconnected");
                    div.children(".connection_status_video").text(data);
                }
            }
        });
    });
    setTimeout(function(){
            update_connection_status();
          }, DISPLAY_CONNECTION_STATUS_TIMER);

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

$("#video_stream_selector").change(function(){
    $.ajax({
        url: 'set_video_stream',
        type: 'post',
        data: {"stream":$("#video_stream_selector").val()},
        success:function(data){
            console.log("video stream changed");
        }
    });
})


function draw_chart(display_div_id,data_div_id){
    Highcharts.chart(display_div_id, {
        chart: {
            type: 'spline',
            backgroundColor: '#000000',
            style:{
                color:'#FFFFFF',
            },
            animation: Highcharts.svg, // don't animate in old IE
            marginRight: 10,
            events: {
                load: function () {
                    // set up the updating of the chart each second
                    var series = this.series[0];
                    setInterval(function () {
                        var x = (new Date()).getTime(), // current time
                            y = Number($("#"+data_div_id).text());
                        var shift = (series.data.length >= 30);
                        series.addPoint([x, y], true, shift);
                    }, GRAPH_TIMER);
                }
            }
        },

        time: {
            useUTC: false
        },
        title:{
            text:''
        },

        xAxis: {
            type: 'datetime',
            tickPixelInterval: 150,
            labels: {
               enabled: false
           },
        },
        yAxis: {
            title: {
                text: ''
            },
            labels: {
               enabled: false
           },
        },
        legend: {
            enabled: false
        },
        exporting: {
            enabled: false
        },

         plotOptions: {
        series: {
            color: graph_color
        }
    },

        series: [{
            name: 'Count',
            data: []            
        }]
    });
}
