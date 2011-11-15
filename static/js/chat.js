var Chat = (function($) {
  var $chatElements;
  var $messageContainer;
  var $inputContainer;
  var $loginButton;
  var $logoutButton;
  var $loginElements;
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
    $(document).scrollTop($(document).height() + 500);
  }

  var setChatDisplay = function (enabled) {
    $loginElements.toggle(!enabled);
    $chatElements.toggle(enabled);
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
        setChatDisplay(true);
        $loginErrors.toggle(false);
        $composeMessageField.focus();
        poll();
      },
      error: function(XMLHttpRequest, textStatus, errorThrown) {
        $loginErrors.text(errorThrown);
        $loginErrors.toggle(true);
      }
    });
  };

  var logout = function() {
    setChatDisplay(false);
    $.ajax({
      type: "DELETE",
      url: "/login/" + username,
      async: true,
      cache: false,
      timeout: 30000,
      success: function(data){
        username = undefined;
        toggleDisplay(false);
        $usernameField.focus();
      },
      error: function(XMLHttpRequest, textStatus, errorThrown) {
        displayMessages([{
          timestamp: '',
          timestamp: '',
          nickname: 'system',
          message: errorThrown,
          msgtype: textStatus
        }], '#messages', 0);
      }
    });
  }

  var displayMessages = function(messages) {
    $(messages).each(function(){
      $messageContainer.append(renderMessage(this));
      lastMessageTimestamp = this.timestamp;
    });
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

    $.ajax({
      type: 'POST',
      url: '/feed',
      data: 'nickname=' + username + '&message=' + message,
      success: function(){
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
      },
      error: function(XMLHttpRequest, textStatus, errorThrown) {
        displayMessages([{
          timestamp: '',
          nickname: 'system',
          message: errorThrown,
          msgtype: textStatus
        }], '#messages', lastMessageTimestamp);
      },
      complete: function() {
        poll();
      }
    });
  };

  var buildChatWindow = function(config) {
    $chatElements = $(config.chatElements);
    $messageContainer = $(config.messageContainer);
    $inputContainer = $(config.inputContainer);
    $loginButton = $(config.loginButton);
    $logoutButton = $(config.logoutButton);
    $loginElements = $(config.loginElements);
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

    $logoutButton.click(function(event) {
      logout();
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

    $(window).unload(function(event){
      logout();
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


