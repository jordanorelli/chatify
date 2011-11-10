var since_timestamp = 0;

var $nick;
var $messages;

function addmsg(msg) {
  var chat_message = '';
  for (var i = 0; i <  msg.messages.length; i++) {
    chat_message = msg.messages[i];
    $("#messages").prepend(
      "<div class='msg "+ msg.msgtype +"'>"+  chat_message.nickname + ": " + chat_message.message +"</div>"
    );
  }
  return  chat_message.timestamp;
}

function waitForMsg() {
  $.ajax({
    type: "GET",
    url: "/feed",
    async: true,
    cache: false,
    timeout:50000,
    data: 'since_timestamp=' + since_timestamp,
    success: function(data) {
      since_timestamp = addmsg(data);
      setTimeout('waitForMsg()', 1000);
    },
    error: function(XMLHttpRequest, textStatus, errorThrown) {
      addmsg({
        timestamp: '',
        nickname: errorThrown,
        messagr: textStatus,
        msgtype: 'error',
      });
      setTimeout('waitForMsg()', "15000");
    },
  });
};

$(document).ready(function(){
  waitForMsg();
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
        success: function(){ $messageBox.val("");  },
        error: function(){ alert("unable to send message!");},
        complete: function(){
          $messageBox.removeAttr("disabled");
          $('#send').removeAttr("disabled");
        }
      });
    }
  });
});
