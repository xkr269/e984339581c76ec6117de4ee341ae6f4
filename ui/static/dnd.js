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

$('.drop').droppable({
  drop : function(e){
        var zone = $(this).attr('id');
        $.ajax({
            url: 'deploy_new_country',
            type: 'post',
            data: {"country":zone},
            success:function(data){
                $("#"+zone+"_docker_image").show();
            }
        });
    }
}); // ce bloc servira de zone de 


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


$(function(){

    $('.drag').draggable({revert:true,revertDuration: 0}); // appel du plugin

});



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



$("#replicate_streams").click(function(){
    $("#replicate_streams").text("Replicating ...");
    $.ajax({
        url: 'replicate_streams',
        type: 'get',
        success:function(data){
            setTimeout(function(){
              $("#replicate_streams").text("Replicate streams");
              $("#global_streams").show();
            }, 1000 * 10);
          }
    });
});


function display_countries(){
    $.ajax({
        url: 'get_deployed_countries',
        type: 'get',
        success:function(data){
            var current_countries = JSON.parse(data);
            console.log(current_countries);
            // Iterate over object
            $.each(current_countries,function(index,value){
                // get chart
                if (contains(deployed_countries,value)){
                  $("#" + value + "_docker_image").show();
                }
            });
            $.each(deployed_countries,function(index,value){
                // get chart
                if (!contains(current_countries,value)){
                  $("#" + value + "_docker_image").hide();
                }
            });
            deployed_countries = current_countries;
            setTimeout(function(){
                display_countries();
              }, 1000);
        }
    });
}





function create_chart(country){
    console.log("creating chart for " + country);
    if (!$('#'+ country + "_chart").length){
        $("#" + country + "_charts").append("<div class='dnd_charts' id='"+country+"_chart'></div>");
    }
    var chart_div = country+"_chart";
    var myChart = Highcharts.chart(chart_div, {
        chart: {
            type: 'column',
            height : 200,
            width : 300,
/*            backgroundColor:'rgba(255, 255, 255, 0.0)'
*/        },
        title: {
            text: country
        },
        xAxis: {
            categories: [],
            labels:
              {
                enabled: false
              }
        },
        yAxis: {
            title: {
                text: 'Count'
            }
        },
        series: [{
            showInLegend: false, 
            data: []
        }]
    });
    return myChart;

}


function update_country_charts(){
    console.log("update country charts");
    $.ajax({
        url: 'get_country_stream_data',
        type: 'get',
        success:function(data){
            loaded_data = JSON.parse(data);
            // Iterate over object
            $.each(loaded_data,function(key,value){
                console.log(key);
                // get or create chart
                if (!$('#' + key + "_chart").length){
                    create_chart(key);
                }
                var chart=$("#" + key + "_chart").highcharts();
                // get and update values
                var chart_data = chart.series[0].data;
                //console.log(chart_data);
                var new_data = [];
                var categories = [];
                for (var i = 0; i < chart_data.length; i++) {
                    category = chart_data[i].category;
                    categories.push(category);
                    current_value = chart_data[i].y;
                    incoming_value = value[category];
                    if (incoming_value){
                        new_value = current_value + incoming_value;
                    }else{
                        new_value = current_value;
                    }
                    new_data.push(new_value);
                    delete value[category];
                }
                for (var category in value){
                    if (category != "count"){
                        categories.push(category);
                        new_data.push(value[category]);                        
                    }
                }
                chart.xAxis[0].setCategories(categories);
                chart.series[0].setData(new_data);  
            })
            
            setTimeout(function(){
                update_country_charts();
              }, 1000 * 2);
        }
    });
}


$( ".show_chart" ).mouseover(function() {
  var country = $(this).attr("id").split('_')[0];
  $("#"+country+"_charts").show();
});

$( ".show_chart" ).mouseout(function() {
  var country = $(this).attr("id").split('_')[0];
  $("#"+country+"_charts").hide();
});


$( document ).ready(function(){
  display_streams();
  display_countries();
  update_country_charts();
});
