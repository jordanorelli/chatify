function addmessages(messages, target_id) {
  var latest_timestamp = 0;
  for (var i = 0; i <  messages.length; i++) {
    var m = messages[i];
    if (m.timestamp > latest_timestamp) {
      latest_timestamp = m.timestamp;
    }
    $(target_id).prepend(
      "<div class='messages "+ messages.msgtype +"'>"+  m.nickname + ": " +
        m.message +"</div>"
    );
  }
  return latest_timestamp;
}

function waitForMsg(since_timestamp) {
  $.ajax({
    type: "GET",
    url: "/feed",
    async: true,
    cache: false,
    timeout:50000,
    data: 'since_timestamp=' + since_timestamp,
    success: function(data) {
      since_timestamp = addmessages(data.messages, '#messages');
      console.log("waitForMsg success block hit.");
      setTimeout('waitForMsg(' + since_timestamp + ')', 1000);
    },
    error: function(XMLHttpRequest, textStatus, errorThrown) {
      addmessages({
        timestamp: '',
        nickname: errorThrown,
        messagr: textStatus,
        msgtype: 'error',
      });
      setTimeout('waitForMsg(' + since_timestamp + ')', "15000");
      alert("OH FUCK");
    },
  });
};

$(document).ready(function(){
  var since_timestamp = 0;
  var $nickField = $('#nickname');
  var $messageBox = $('#message');

  $nickField.focus();

  $nickField.keypress(function(event){
    if($(this).val()!=''){
      $messageBox.removeAttr("disabled");
      $('#send').removeAttr("disabled");
    } else {
      $messageBox.attr("disabled", "disabled");
      $('#send').attr("disabled", "disabled");
    }
  });

  $nickField.change(function(event){
    if($(this).val()!=''){
      $(this).attr("disabled", "disabled");
      $messageBox.focus();
    }
  });

  $('#send').click(function(event){
    $this = $(this);
    if($messageBox.val()!=''){
      var message = $messageBox.val();
      var nickname = $('#nickname').val();
      // disable changing our name
      $this.attr("disabled", "disabled");
      // enable sending new messages
      $messageBox.attr("disabled","disabled");
      $.ajax({
        type: 'POST',
        url: '/feed',
        data: 'nickname=' + nickname + '&message=' + message,
        success: function(){
          console.log("Hit send success block.");
          $messageBox.val("")
        },
        error: function(){ alert("unable to send message!");},
        complete: function(){
          $messageBox.removeAttr("disabled");
          $('#send').removeAttr("disabled");
        }
      });
    }
  });

  waitForMsg(since_timestamp);
});
