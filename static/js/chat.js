function sanitize(text) {
    "use strict";
    return text.replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
}

function donothing() {
    return false;
}

function addmessages(messages,
    target_id, since_timestamp) {
    "use strict";
    var date = new Date(), m, i, timeFormatted;

    for (i = 0; i < messages.length; i++) {
        m = messages[i];
        if (m.timestamp > since_timestamp) {
            since_timestamp = m.timestamp;
        }
        date.setTime(m.timestamp * 1000);
        timeFormatted = date.toString().split(' ')[4];
        $(target_id).append(
            '<div class="message-item ' + m.msgtype + '">' +
                '<span class="message-nickname">' + sanitize(m.nickname) +
                    '</span>' +
                '<span class="message-text">' + sanitize(m.message) +
                    '</span>' +
                '<span class="message-time">' + timeFormatted  +
                    '</span>' +
                '</div>'
        );
        $(document).scrollTop($(document).height() + 500);
    }
    return since_timestamp;
}


function waitForMsg(since_timestamp) {
    "use strict";
    $.ajax({
        type: "GET",
        url: "/feed",
        async: true,
        cache: false,
        timeout: 50000,
        data: 'since_timestamp=' + since_timestamp,
        success: function (data) {
            since_timestamp = addmessages(data.messages,
                '#messages', since_timestamp);
            console.log("waitForMsg success block hit.");
            setTimeout('waitForMsg(' + since_timestamp + ')',
                1000);
        },
        error: function (XMLHttpRequest, textStatus, errorThrown) {
            addmessages([{
                timestamp: '',
                nickname: 'system',
                message: errorThrown,
                msgtype: textStatus
            }], '#messages', since_timestamp);
            setTimeout('waitForMsg(' + since_timestamp + ')',
                15000);
        }
    });
}


function login(nickname) {
    "use strict";
    console.log("Logging in as " + nickname);
    $.ajax({
        type: "POST",
        url: "/login/" + escape(nickname),
        async: true,
        cache: false,
        timeout: 30000,
        success: function (data) {
            $("#login-form").css("display", "none");
            $("#messages").css("display", "block");
            $("#send-form").css("display", "block");
            $("#whoiam").html(sanitize($("#nickname").val()) + " : ");
            $("#message").focus();
        },
        error: function (XMLHttpRequest, textStatus, errorThrown) {
            addmessages([{
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
    "use strict";
    console.log("Logging out " + nickname);
    $.ajax({
        type: "DELETE",
        url: "/login/" + escape(nickname),
        async: true,
        cache: false,
        timeout: 30000,
        success: function (data) {
            $("#send-form").css("display", "none");
            $("#messages").css("display", "none");
            $("#login-form").css("display", "block");
            $("#whoiam").html("anonymous : ");
            $("#nickname").focus();
        },
        error: function (XMLHttpRequest, textStatus, errorThrown) {
            addmessages([{
                timestamp: '',
                nickname: 'system',
                message: errorThrown,
                msgtype: textStatus
            }], '#messages', 0);
        }
    });
}


$(document).ready(function () {
    "use strict";
    var since_timestamp = 0,
        $nickField   = $("#nickname"),
        $messageBox  = $("#message"),
        $loginForm   = $("#login-form"),
        $sendForm    = $("#send-form"),
        $loginButton = $("#login"),
        $sendButton  = $("#send");

    $nickField.focus();

    $(window).unload(function (event) {
        logout($("#nickname").val().trim());
    });

    $nickField.keypress(function (event) {
        var nickname = $(this).val().trim();
        if (nickname !== '') {
            $("#login").removeAttr("disabled");
        } else {
            $("#login").attr("disabled", "disabled");
        }
    });

    $messageBox.keypress(function (event) {
        var message = $(this).val().trim();
        if (message !== '') {
            $("#send").removeAttr("disabled");
        } else {
            $("#send").attr("disabled", "disabled");
        }
    });


    $loginButton.click(function (event) {
        var nickname = $("#nickname").val().trim();
        if (nickname !== '') {
            $("#nickname").attr("disabled", "disabled");
            $(this).attr("disabled", "disabled");
            login(nickname);
        }
        event.stopPropagation();
        return false;
    });

    $sendButton.click(function (event) {
        var $this = $(this),
            message = $("#message").val(),
            nickname = $('#nickname').val();
        if ($("#message").val().trim() !== '') {
            // disable sending twice
            $(this).attr("disabled", "disabled");
            $("#message").attr("disabled", "disabled");
            $.ajax({
                type: 'POST',
                url: '/feed',
                data: 'nickname=' + escape(nickname) +
                    '&message=' + escape(message),
                success: function () {
                    $("#message").val("");
                },
                error: function () {
                    alert("unable to send message!");
                },
                complete: function () {
                    $("#message").removeAttr("disabled");
                    $("#send").removeAttr("disabled");
                }
            });
        }
        event.stopPropagation();
        return false;
    });

    //if (auto_login === true) {
    //    login($("nickname").val());
    //}

    waitForMsg(since_timestamp);
});
