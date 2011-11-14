var Chat = (function($) {
  var $chatContainer;
  var $messageContainer;
  var $inputContainer;
  var $loginButton;
  var $loginContainer;
  var $loginErrors;
  var $usernameField;
  var $usernameDisplay;
  var $sendMessageButton;
  var $composeMessageField;
  var messageTemplate;
  var username;
  var pollID;
  var pollInterval = 30000;
  var lastMessageTimestamp = 0;

  var sanitize = function(text) {
    return text.replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
  }

  var scrollToEnd = function() {
    console.log("Scroll!");
    $(document).scrollTop($(document).height() + 500);
  }

  var login = function() {
    var desiredUsername = $usernameField.val().trim();
    $.ajax({
      type: "POST",
      url: "/login/" + desiredUsername,
      async: true,
      cache: false,
      timeout: 30000,
      success: function(data){
        username = sanitize(desiredUsername);
        $usernameDisplay.html(username);
        $loginContainer.hide();
        $loginErrors.hide();
        $chatContainer.show();
        poll();
      },
      error: function(XMLHttpRequest, textStatus, errorThrown) {
        console.log(errorThrown);
        $loginErrors.text(errorThrown);
        $loginErrors.show();
      }
    });
  };

  var displayMessages = function(messages) {
    $(messages).each(function(){
      $messageContainer.append(renderMessage(this));
      lastMessageTimestamp = this.timestamp;
    });
    console.log(lastMessageTimestamp);
    scrollToEnd();
  };

  var renderMessage = function(message) {
    var date = new Date();
    date.setTime(message.timestamp);
    message.formattedTime = date.toString().split(' ')[4];
    return Mustache.to_html(messageTemplate, message);
  };

  var setButtonBehavior = function($inputField, $submitButton){
    var value = $inputField.val().trim();
    if(value){
      $submitButton.removeAttr("disabled");
    } else {
      $submitButton.attr("disabled", "disabled");
    }
  };

  var sendMessageClick = function(event) {
    var $this = $(this);
    var message = $composeMessageField.val();
    $this.attr("disabled", "disabled");
    $composeMessageField.blur();
    $composeMessageField.attr("disabled", "disabled");

    console.log("Attempting to send message: " + message);
    $.ajax({
      type: 'POST',
      url: '/feed',
      data: 'nickname=' + username + '&message=' + message,
      success: function(){
        console.log("Hit send success block.");
        $composeMessageField.val("");
      },
      error: function(XMLHttpRequest, textStatus, errorThrown) {
        console.log(errorThrown);
      },
      complete: function(){
        $composeMessageField.removeAttr("disabled");
        $composeMessageField.focus();
        $this.removeAttr("disabled");
      }
    });

    event.preventDefault();
    event.stopPropagation();
    return false;
  };

  var poll = function() {
    $.ajax({
      type: "GET",
      url: "/feed",
      async: true,
      cache: false,
      timeout: pollInterval,
      data: 'since_timestamp=' + lastMessageTimestamp,
      success: function(data) {
        displayMessages(data.messages);
        poll();
      },
      error: function(XMLHttpRequest, textStatus, errorThrown) {
        displayMessages([{
          timestamp: '',
          nickname: 'system',
          message: errorThrown,
          msgtype: textStatus
        }], '#messages', since_timestamp);
        poll();
      }
    });
  };

  var buildChatWindow = function(config) {
    $chatContainer = $(config.chatContainer);
    $messageContainer = $(config.messageContainer);
    $inputContainer = $(config.inputContainer);
    $loginButton = $(config.loginButton);
    $loginContainer = $(config.loginContainer);
    $loginErrors = $(config.loginErrors);
    $sendMessageButton = $(config.sendMessageButton);
    $composeMessageField = $(config.composeMessageField);
    $usernameField = $(config.usernameField);
    $usernameDisplay = $(config.usernameDisplay);
    messageTemplate = config.messageTemplate;

    $loginButton.click(function(event) {
      login();
      event.preventDefault();
    });

    $composeMessageField.keyup(function(event) {
      setButtonBehavior($(this), $sendMessageButton);
    });

    $composeMessageField.keydown(function(event) {
      switch(event.keyCode) {
        case 13: // enter
          if(!event.shiftKey)
            $sendMessageButton.click();
          break;
      }
    });

    $usernameField.keyup(function(event) {
      setButtonBehavior($(this), $loginButton);
    });

    $sendMessageButton.click(function(event) {
      sendMessageClick(event);
    });
  };

  var doNothing = function() {
    return false;
  };

  return {
    buildChatWindow: buildChatWindow,
    doNothing: doNothing
  };
})($);

// function logout(nickname) {
//   console.log("Logging out " + nickname);
//   $.ajax({
//     type: "DELETE",
//     url: "/login/" + escape(nickname),
//     async: true,
//     cache: false,
//     timeout: 30000,
//     success: function(data){
//       $("#send-form").css("display", "none");
//       $("#messages").css("display", "none");
//       $("#login-form").css("display", "block");
//       $("#whoiam").html("anonymous : ");
//       $("#nickname").focus();
//     },
//     error: function(XMLHttpRequest, textStatus, errorThrown) {
//       displayMessages([{
//         timestamp: '',
//         timestamp: '',
//         nickname: 'system',
//         message: errorThrown,
//         msgtype: textStatus
//       }], '#messages', 0);
//     }
//   });
// }

// $(document).ready(function(){
//   $(window).unload(function(event){
//     logout($nickField.val().trim());
//   });
//   $messageBox.keypress(function(event){
//     var message = $(this).val().trim();
//     if(message!=''){
//       $sendButton.removeAttr("disabled");
//     } else {
//       $sendButton.attr("disabled", "disabled");
//     }
//   });
// 
//   $loginButton.click(function(event){
//     var nickname = $nickField.val().trim();
//     if(nickname!=''){
//         $nickField.attr("disabled", "disabled");
//         $(this).attr("disabled", "disabled");
//         login(nickname);
//     }
//     event.stopPropagation();
//     return false;
//   });
// 
//   $sendButton.click(function(event){
//     if($messageBox.val().trim()!=''){
//       var message = $messageBox.val();
//       var nickname = $nickField.val().trim();
//       // disable sending twice
//       $(this).attr("disabled", "disabled");
//       $messageBox.attr("disabled","disabled");
//       $.ajax({
//         type: 'POST',
//         url: '/feed',
//         data: 'nickname=' + escape(nickname) + '&message=' + escape(message),
//         success: function(){
//           console.log("Hit send success block.");
//           $messageBox.val("")
//         },
//         error: function(){ alert("unable to send message!");},
//         complete: function(){
//           $messageBox.removeAttr("disabled");
//           $(this).removeAttr("disabled");
//         }
//       });
//     }
//     event.stopPropagation();
//     return false;
//   });
// 
//   getMessages(since_timestamp);
// });
