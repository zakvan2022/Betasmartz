$('a[href^="#"]').on('click', function(event) {

    var target = $(this.getAttribute('href'));

    if( target.length ) {
      event.preventDefault();
      $('html, body').stop().animate({
          scrollTop: target.offset().top
      }, 1000);
    }

});

$('#click').click(function()
{   
    $("#panel").animate({width:'toggle'},350);    
});


document.getElementById('closeButton').addEventListener('click', function(e) {
    e.preventDefault();
    this.parentNode.style.display = 'none';
}, false);


if($('#render_type').val() == 'html') {
  var pk = $("#pk").val()
  var data = { 'csrfmiddlewaretoken': $('[name="csrfmiddlewaretoken"]').val()}
  $.getJSON({
    url: pk + '/chart_configs',
    type : 'POST',
    data : data,
    success: function (data) {
      if(data !== null) {
        for (var key in data) {
          Highcharts.chart(key, data[key])
        }
      }
    }
  })
}
