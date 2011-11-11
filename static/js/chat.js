function addmessages(messages, target_id, since_timestamp) {
  for (var i = 0; i < messages.length; i++) {
    var m = messages[i];
    if (m.timestamp > since_timestamp) {
      since_timestamp = m.timestamp;
    }
    $(target_id).prepend(
      "<div class='messages "+ m.msgtype +"'>"+  m.nickname + ": " +
        m.message +"</div>"
    );
  }
  return since_timestamp;
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
      since_timestamp = addmessages(data.messages, '#messages', since_timestamp);
      console.log("waitForMsg success block hit.");
      setTimeout('waitForMsg(' + since_timestamp + ')', 1000);
    },
    error: function(XMLHttpRequest, textStatus, errorThrown) {
      since_timestamp = addmessages([{
        timestamp: '',
        nickname: errorThrown,
        messagr: textStatus,
        msgtype: 'error',
      }], '#messages', since_timestamp);
      setTimeout('waitForMsg(' + since_timestamp + ')', "15000");
      alert("OH FUCK");
    },
  });
};

function login(nickname) {
  console.log("Logging in as " + nickname);
  $.ajax({
    type: "POST",
    url: "/login",
    async: true,
    cache: false,
    timeout: 30000,
    data: 'nickname=' + nickname,
    success: function(data){
      $("#login-form").css("display", "none");
      $("#send-form").css("display", "block");   
      $("#whoiam").html($("#nickname").val() + " : ");
      $("#message").focus();
    },
    error: function(data, errorText){
      $("#nickname").removeAttr("disabled");
      $("#login").removeAttr("disabled");
    }
  });
}

$(document).ready(function(){
  var since_timestamp = 0;
  var $nickField = $('#nickname');
  var $messageBox = $('#message');
  var $loginForm = $('#login-form');
  var $sendForm = $('#send-form');
  var $loginButton = $('#login');
  var $sendButton = $('#send');

  $nickField.focus();

  $nickField.change(function(event){
    var nickname = $(this).val();
    if(nickname!=''){
      $(this).attr("disabled", "disabled");
      $("login").attr("disabled","disabled");
      login(nickname);
    }
  });

  $loginButton.click( function(event){
    var nickname = $("nickname").val();
    if(nickname!=''){
        $("nickname").attr("disabled", "disabled");
        $(this).attr("disabled", "disabled");
        login(nickname);
    }
  });
  $sendButton.click(function(event){
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
