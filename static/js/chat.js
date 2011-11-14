/* Adds messages to the chat log.
* @messages - an array of messages.
* @target_id - DOM ID of the element that we will inject the message element into
*/
function addmessages(messages, target_id, since_timestamp) {
  for (var i = 0; i < messages.length; i++) {
    var m = messages[i];
    if (m.timestamp > since_timestamp) {
      since_timestamp = m.timestamp;
    }
    $(target_id).append(renderMessage(m));
    $(document).scrollTop($(document).height()+500);
  }
  return since_timestamp;
}

/* given a message object, returns a string representation of the message. */
function renderMessage(message) {
  var date = new Date();
  date.setTime(message.timestamp * 1000);
  var timeFormatted = date.toString().split(' ')[4];
  return '<div class="message-item ' + message.msgtype + '">' +
    '<span class="message-nickname">' + sanitize(message.nickname)     + '</span>' +
    '<span class="message-text">'     + sanitize(message.message)      + '</span>' +
    '<span class="message-time">'     + timeFormatted  + '</span>' +
    '</div>';
}

function sanitize(text) {
    return text.replace(/&/g, "&amp;")
               .replace(/</g, "&lt;")
               .replace(/>/g, "&gt;");
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
      addmessages([{
        timestamp: '',
        nickname: 'system',
        message: errorThrown,
        msgtype: textStatus
      }], '#messages', since_timestamp);
      setTimeout('waitForMsg(' + since_timestamp + ')', "15000");
    },
  });
};

function login(nickname) {
  console.log("Logging in as " + nickname);
  $.ajax({
    type: "POST",
    url: "/login/" + escape(nickname),
    async: true,
    cache: false,
    timeout: 30000,
    success: function(data){
      $("#login-form").css("display", "none");
      $("#messages").css("display", "block");
      $("#send-form").css("display", "block");
      $("#whoiam").html(sanitize($("#nickname").val()) + " : ");
      $("#message").focus();
    },
    error: function(XMLHttpRequest, textStatus, errorThrown) {
      since_timestamp = addmessages([{
        timestamp: '',
        nickname: 'system',
        message: errorThrown,
        msgtype: textStatus
      }], '#messages', 0);

      $("#nickname").removeAttr("disabled");
      $("#login").removeAttr("disabled");
    }
  });
}

function logout(nickname) {
  console.log("Logging out " + nickname);
  $.ajax({
    type: "DELETE",
    url: "/login/" + escape(nickname),
    async: true,
    cache: false,
    timeout: 30000,
    success: function(data){
      $("#send-form").css("display", "none");
      $("#messages").css("display", "none");
      $("#login-form").css("display", "block");
      $("#whoiam").html("anonymous : ");
      $("#nickname").focus();
    },
    error: function(XMLHttpRequest, textStatus, errorThrown) {
      addmessages([{
        timestamp: '',
        timestamp: '',
        nickname: 'system',
        message: errorThrown,
        msgtype: textStatus
      }], '#messages', 0);
    }
  });
}

$(document).ready(function(){
  var since_timestamp = 0;
  var $nickField   = $("#nickname"  );
  var $messageBox  = $("#message"   );
  var $loginForm   = $("#login-form");
  var $sendForm    = $("#send-form" );
  var $loginButton = $("#login"     );
  var $sendButton  = $("#send"      );

  $nickField.focus();

  $(window).unload(function(event){
    logout($("#nickname").val().trim());
  });

  $nickField.keypress(function(event){
    var nickname = $(this).val().trim();
    if(nickname!=''){
      $("#login").removeAttr("disabled");
    } else {
      $("#login").attr("disabled", "disabled");
    }
  });

  $messageBox.keypress(function(event){
    var message = $(this).val().trim();
    if(message!=''){
      $("#send").removeAttr("disabled");
    } else {
      $("#send").attr("disabled", "disabled");
    }
  });

  $loginButton.click( function(event){
    var nickname = $("#nickname").val().trim();
    if(nickname!=''){
        $("#nickname").attr("disabled", "disabled");
        $(this).attr("disabled", "disabled");
        login(nickname);
    }
    event.stopPropagation();
    return false;
  });

  $sendButton.click(function(event){
    var $this = $(this);
    if($("#message").val().trim()!=''){
      var message = $("#message").val();
      var nickname = $('#nickname').val();
      // disable sending twice
      $(this).attr("disabled", "disabled");
      $("#message").attr("disabled","disabled");
      $.ajax({
        type: 'POST',
        url: '/feed',
        data: 'nickname=' + escape(nickname) + '&message=' + escape(message),
        success: function(){
          console.log("Hit send success block.");
          $("#message").val("")
        },
        error: function(){ alert("unable to send message!");},
        complete: function(){
          $("#message").removeAttr("disabled");
          $("#send"   ).removeAttr("disabled");
        }
      });
    }
    event.stopPropagation();
    return false;
  });

  waitForMsg(since_timestamp);
});
