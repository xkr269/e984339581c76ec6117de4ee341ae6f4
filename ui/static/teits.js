// js file for TEITS main UI


var DISPLAY_COUNT_TIMER = 1000
var DISPLAY_SPEED_TIMER = 1000
var DISPLAY_CONNECTION_STATUS_TIMER = 1000
var DISPLAY_BATTERY_TIMER = 5000
var PATROL_TIMER = 5000
var GRAPH_TIMER = 2000 
var graph_color = "#6CFC5F"



patrol_in_progess = false;

$(function(){
    $('.drag').draggable({revert:"invalid",revertDuration: 300}); // appel du plugin
});



function set_drone_position(drone_id,drop_zone,action){
    console.log("Set " + drone_id + " position to " + drop_zone + " , action : " + action)
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
    var parentOffset = $(this).parent().offset(); 
    $('#drone_1').animate({
            top : e.pageY - parentOffset.top - $('#drone_1').height()/2,
            left: e.pageX - parentOffset.left - $('#drone_1').width()/2
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
        if($(this).css('display')!='none'){move_to_position($(this).attr("id"),"home_base","land");}
    })
})

$("#land_button").click(function(){
    $(".drone").each(function(){
        console.log("Landing");
        patrol_in_progess = false;
        drone_id = $(this).attr("id");
        $.ajax({
            url: 'land',
            type: 'post',
            data: {"drone_id":drone_id},
            success:function(data){
                console.log(data)
            }
        });
    })
})

$("#land_button").click(function(){
    $(".drone").each(function(){
        console.log("Landing");
        patrol_in_progess = false;
        drone_id = $(this).attr("id");
        $.ajax({
            url: 'reset_position',
            type: 'post',
            data: {"drone_id":drone_id},
            success:function(data){
                console.log(data)
            }
        });
    })
})

$("#new_drone_button").click(function(){
        if (!$("#drone_1_ui").is(":visible")){
            $("#drone_1").show()
            $("#drone_1_ui").show();
            $("#drone_1_video").attr("src","video_stream/drone_1");
            draw_chart("drone_1_count_graph","drone_1_count");
            set_drone_position("drone_1","home_base","takeoff");
            refresh_battery_pct("drone_1");
            refresh_speed("drone_1");
            refresh_count("drone_1");

        }
        else if (!$("#drone_2_ui").is(":visible")){
            $("#archi").hide();
            $("#drone_2").show();
            $("#drone_2_ui").show();
            $("#drone_2_video").attr("src","video_stream/drone_2");
            draw_chart("drone_2_count_graph","drone_2_count");
            set_drone_position("drone_2","home_base","takeoff");
            refresh_battery_pct("drone_2");
            refresh_speed("drone_2");
            refresh_count("drone_2");
        }
        else {
            $("#drone_3").show();
            $("#drone_3_ui").show();
            $("#drone_3_video").attr("src","video_stream/drone_3");
            draw_chart("drone_3_count_graph","drone_3_count");
            set_drone_position("drone_3","home_base","takeoff");
            refresh_battery_pct("drone_3");
            refresh_speed("drone_3");
            refresh_count("drone_3");
        }
})


$("#patrol_button").click(function(){
    console.log("Start patroling");
    patrol_in_progess = true;
    patrol();
})

$("#architecture_button").click(function(){
    var archi_div = $("#archi");
    if(archi_div.is(":visible")){
        archi_div.hide();
    }else{
        archi_div.show();
    }
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



function refresh_battery_pct(drone_id){
    $.ajax({
        url: 'get_battery_pct',
        type: 'post',
        data: {"drone_id":drone_id},
        success:function(data){
            $("#"+drone_id+"_battery_pct").text(data+"%");
            set_battery_gauge(drone_id);
        }
    });
    setTimeout(function(){
        refresh_battery_pct(drone_id);
    }, DISPLAY_BATTERY_TIMER);
}

function set_battery_gauge(drone_id){
    var battery_pct = parseInt($("#"+drone_id+"_battery_pct").text().slice(0,-1));
    var gauge_div = $("#"+drone_id+"_battery_gauge");

    if(battery_pct > 75){
        gauge_div.css("background-image", "url(/static/battery_100.png)");
    } 
    else if(battery_pct > 50){
        gauge_div.css("background-image", "url(/static/battery_75.png)");
    } 
    else if(battery_pct > 25){
        gauge_div.css("background-image", "url(/static/battery_50.png)");
    } 
    else if(battery_pct > 15){
        gauge_div.css("background-image", "url(/static/battery_25.png)");
    }
    else {
        gauge_div.css("background-image", "url(/static/battery_15.png)");
    }
}


function refresh_speed(drone_id){
    $.ajax({
        url: 'get_battery_pct',
        type: 'post',
        data: {"drone_id":drone_id},
        success:function(data){
            $("#"+drone_id+"_speed").text(data);
        }
    });
    setTimeout(function(){
        refresh_speed(drone_id);
    }, DISPLAY_BATTERY_TIMER);
}


function refresh_global_count(){
    var count = 0;
    $(".count").each(function(){
        var div = $(this);
        if(div.is(":visible")){
            count = count + Number(div.text());
        }
    });
    $("#global_count").text(count);
    setTimeout(function(){
        refresh_global_count();
    }, DISPLAY_COUNT_TIMER);
}

function refresh_count(drone_id){
    $.ajax({
        url: 'get_count',
        type: 'post',
        data: {"drone_id":drone_id},
        success:function(data){
            $("#"+drone_id+"_count").text(data);
        }
    });
    setTimeout(function(){
            refresh_count(drone_id);
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

$("#source_display").click(function(){
    $.ajax({
        url: 'set_video_stream',
        type: 'post',
        data: {"stream":"source"},
        success:function(data){
            console.log("video stream changed to source");
            $("#processed_tick").hide();
            $("#source_tick").show();
        }
    });
})

$("#processed_display").click(function(){
    $.ajax({
        url: 'set_video_stream',
        type: 'post',
        data: {"stream":"procesed"},
        success:function(data){
            console.log("video stream changed to processed");
            $("#source_tick").hide();
            $("#processed_tick").show();
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




$( document ).ready(function() {
    // Position drones images on the home_base zone
    var hb = $("#home_base");
    var hb_top = hb.position().top / hb.parent().height() * 100;
    var hb_left = hb.position().left / hb.parent().width() * 100;;
    var hb_height = hb.height() / hb.parent().height() * 100;
    var hb_width = hb.width() / hb.parent().width() * 100;
    console.log(hb_top + " : " + hb_left + " : " + hb_height  + " : " +  hb_width )
    $(".drone").each(function(){
        $(this).css({top: hb_top + "%",
                     left: hb_left  + "%",
                     position: 'absolute'});
        });

    // Hide drones UIs
    $(".drone_ui").each(function(){if($(this).attr("id") != "drone_1_ui"){$(this).hide();}});
    $(".drone").each(function(){$(this).hide();});
    
    // Set global count and chart
    refresh_global_count();
    draw_chart("global_count_graph","global_count");
    if($("#source_selector").attr("display")=="source"){
        $("#source_tick").show();
    }else{
        $("#processed_tick").show();
    }
});




var dropdown = document.getElementsByClassName("dropdown-btn");
var i;

for (i = 0; i < dropdown.length; i++) {
  dropdown[i].addEventListener("click", function() {
  this.classList.toggle("active");
  var dropdownContent = this.nextElementSibling;
  if (dropdownContent.style.display === "block") {
  dropdownContent.style.display = "none";
  } else {
  dropdownContent.style.display = "block";
  }
  });
}
