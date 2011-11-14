var Chat = (function($) {
  var $chatElements;
  var $messageContainer;
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

  var sanitize = function (text) {
    return text.replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
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
        $chatElements.show();
        poll();
        pollID = setInterval(poll, pollInterval);
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
    });
  };

  var renderMessage = function(message) {
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

//   $sendButton.click(function(event){
//     if($messageBox.val().trim()!=''){
//       var message = $messageBox.val();
//       var nickname = $nickField.val().trim();
//       // disable sending twice
//       $(this).attr("disabled", "disabled");
//       $messageBox.attr("disabled","disabled");
//       $.ajax({
//     event.stopPropagation();
//     return false;
//   });

  var sendMessageClick = function(event) {
    var $this = $(this);
    var message = $composeMessageField.val();
    $this.attr("disabled", "disabled");

    console.log("Attempting to send message: " + message);
    $.ajax({
      type: 'POST',
      url: '/feed',
      data: 'nickname=' + nickname + '&message=' + message,
      success: function(){
        console.log("Hit send success block.");
        $composeMessageField.val("");
      },
      error: function(XMLHttpRequest, textStatus, errorThrown) {
        console.log(errorThrown);
      },
      complete: function(){
        $composeMessageField.removeAttr("disabled");
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
      // data: 'since_timestamp=' + since_timestamp,
      data: 'since_timestamp=' + 0,
      success: function(data) {
        displayMessages(data.messages);
        // since_timestamp = displayMessages(data.messages, '#messages', since_timestamp);
        console.log("getMessages success block hit.");
        // setTimeout(function() {
        //   getMessages(since_timestamp);
        // }, 1000);
      },
      error: function(XMLHttpRequest, textStatus, errorThrown) {
        displayMessages([{
          timestamp: '',
          nickname: 'system',
          message: errorThrown,
          msgtype: textStatus
        }], '#messages', since_timestamp);
        setTimeout(function() {
          getMessages(since_timestamp);
        }, 15000);
      }
    });
  };

  var buildChatWindow = function(config) {
    $chatElements = $(config.chatElements);
    $messageContainer = $(config.messageContainer);
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

    $composeMessageField.keypress(function(event){
      setButtonBehavior($(this), $sendMessageButton);
    });

    $usernameField.keypress(function(event){
      setButtonBehavior($(this), $loginButton);
    });

    $sendMessageButton.click(function(event){
      sendMessageClick(event);
    });

  };

  return {
    buildChatWindow: buildChatWindow
  };
})($);

/* Adds messages to the chat log.
* @messages - an array of messages.
* @target_id - DOM ID of the element that we will inject the message element into
*/
// 
// /* given a message object, returns a string representation of the message. */
// function renderMessage(message) {
//   var date = new Date();
//   date.setTime(message.timestamp * 1000);
//   var timeFormatted = date.toString().split(' ')[4];
//   return '<div class="message-item ' + message.msgtype + '">' +
//     '<span class="message-nickname">' + sanitize(message.nickname)     + '</span>' +
//     '<span class="message-text">'     + sanitize(message.message)      + '</span>' +
//     '<span class="message-time">'     + timeFormatted  + '</span>' +
//     '</div>';
// }
// 
// 
// function getMessages(since_timestamp) {
//   $.ajax({
//     type: "GET",
//     url: "/feed",
//     async: true,
//     cache: false,
//     timeout:50000,
//     data: 'since_timestamp=' + since_timestamp,
//     success: function(data) {
//       since_timestamp = displayMessages(data.messages, '#messages', since_timestamp);
//       console.log("getMessages success block hit.");
//       setTimeout(function() {
//         getMessages(since_timestamp);
//       }, 1000);
//     },
//     error: function(XMLHttpRequest, textStatus, errorThrown) {
//       displayMessages([{
//         timestamp: '',
//         nickname: 'system',
//         message: errorThrown,
//         msgtype: textStatus
//       }], '#messages', since_timestamp);
//       setTimeout(function() {
//         getMessages(since_timestamp);
//       }, 15000);
//     },
//   });
// };
// 
// function login(nickname) {
//   console.log("Logging in as " + nickname);
//   $.ajax({
//     type: "POST",
//     url: "/login/" + escape(nickname),
//     async: true,
//     cache: false,
//     timeout: 30000,
//     success: function(data){
//       $("#login-form").css("display", "none");
//       $("#messages").css("display", "block");
//       $("#send-form").css("display", "block");
//       $("#whoiam").html(sanitize($("#nickname").val()) + " : ");
//       $("#message").focus();
//     },
//     error: function(XMLHttpRequest, textStatus, errorThrown) {
//       since_timestamp = displayMessages([{
//         timestamp: '',
//         nickname: 'system',
//         message: errorThrown,
//         msgtype: textStatus
//       }], '#messages', 0);
// 
//       $("#nickname").removeAttr("disabled");
//       $("#login").removeAttr("disabled");
//     }
//   });
// }
// 
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
// 
// $(document).ready(function(){
//   var since_timestamp = 0;
//   var $nickField   = $("#nickname"  );
//   var $messageBox  = $("#message"   );
//   var $loginForm   = $("#login-form");
//   var $sendForm    = $("#send-form" );
//   var $loginButton = $("#login"     );
//   var $sendButton  = $("#send"      );
// 
//   $nickField.focus();
// 
//   $(window).unload(function(event){
//     logout($nickField.val().trim());
//   });
// 
//   $nickField.keypress(function(event){
//     var nickname = $(this).val().trim();
//     if(nickname!=''){
//       $loginButton.removeAttr("disabled");
//     } else {
//       $loginButton.attr("disabled", "disabled");
//     }
//   });
// 
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
