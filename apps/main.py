#!/usr/bin/env python
from brubeck.request_handling import Brubeck, JSONMessageHandler
from brubeck.templating import load_jinja2_env, Jinja2Rendering
from dictshield import fields
from dictshield.document import Document
from dictshield.fields import EmbeddedDocument, ShieldException
from gevent.event import Event
from urllib import unquote
import os
import time

## hold our messages in memory here, limit to last 20
LIST_SIZE = 50
users_online = []
chat_messages = []
new_message_event = Event()

## Our long polling interval
POLL_INTERVAL = 30

## How old a user must be in seconds to kick them out of the room
USER_TIMEOUT = 60

def add_message(chat_message, chat_messages_list):
    """Adds a message to our message history. A server timestamp is used to
    avoid sending duplicates."""
    chat_messages_list.append(chat_message)

    if len(chat_messages_list) > LIST_SIZE:
        chat_messages_list.pop(0)

    # alert our polling clients
    new_message_event.set()
    new_message_event.clear()


def get_messages(chat_messages_list, since_timestamp=0):
    """get new messages since a certain timestamp"""
    return filter(lambda x: x.timestamp > since_timestamp,
                  chat_messages)

def add_user(user, users_online_list):
    """add a user to our online users. Timestamp used to determine freshness"""
    users_online_list.append(user)

def remove_user(user, users_list):
    users_list.remove(user)

def find_list_item_by_nickname(nickname, target_list):
    """returns the first list item matching a nickname"""
    items = filter(lambda x: x.nickname == nickname,
                   target_list)
    if len(items)==0:
        return None
    else:
        return items[0]

# def check_users_online(users_list, chat_messages_list, since_timestamp=(time.time() - USER_TIMEOUT)):
#     """check for expired users and send a message they left the room"""
#     users = filter(lambda x: x.timestamp <= since_timestamp,
#                    users_list)
#     for user in users:
#         add_message(ChatMessage(nickname='system', message="%s can not been found in the room" % user.nickname),
#                     chat_messages_list)
#         remove_user(user, users_online)

class User(Document):
    """a chat user"""
    timestamp = fields.IntField(required=True)
    nickname = fields.StringField(required=True, max_length=40)

    def __init__(self, *args, **kwargs):
        super(User, self).__init__(*args, **kwargs)
        self.timestamp = int(time.time() * 1000)

class ChatMessage(EmbeddedDocument):
    """A single message"""
    timestamp = fields.IntField(required=True)
    nickname = fields.StringField(required=True, max_length=40)
    message = fields.StringField(required=True)
    msgtype = fields.StringField(default='user',
                          choices=['user', 'error', 'system'])

    def __init__(self, *args, **kwargs):
        super(ChatMessage, self).__init__(*args, **kwargs)
        self.timestamp = int(time.time() * 1000)

class ChatifyHandler(Jinja2Rendering):
    """Renders the chat interface template."""

    def get(self):
        try:
            nickname = self.get_cookie('nickname')
            ## nickname = self.get_cookie('nickname', secret=self.application.cookie_secret)
            auto_login_flag = 'var auto_login = true;'
        except ValueError:
            self.set_cookie('nickname','')
            ##self.set_cookie('nickname','', secret=self.application.cookie_secret)
            nickname = ''
            auto_login_flag = 'var auto_login = false;'

        context = {
            'auto_login_flag': auto_login_flag,
            'nickname': nickname,
        }
        return self.render_template('base.html', context=context)

class FeedHandler(JSONMessageHandler):
    """Handles poll requests from user; sends out queued messages."""

    def prepare(self):
        self.headers = {'Content-Type': 'application/json'}

    def get(self):
        try:
            messages = get_messages(chat_messages, int(self.get_argument('since_timestamp', 0)))

        except ValueError as e:
            print "failed to get message"
            messages = get_messages(chat_messages)

        if len(messages)==0:
            new_message_event.wait(POLL_INTERVAL)
            print "waking up"
            try:
                messages = get_messages(chat_messages, int(self.get_argument('since_timestamp', 0)))
    
            except ValueError as e:
                messages = get_messages(chat_messages)

            self.set_status(200)
            self.add_to_payload('messages', messages)

        else:
            self.set_status(200)
            self.add_to_payload('messages', messages)

        return self.render()

    def post(self):
        nickname = self.get_argument('nickname')
        message = self.get_argument('message')
        print "%s: %s" % (nickname, message)
        chat_message = ChatMessage(**{'nickname': nickname, 'message': message})

        try:
            chat_message.validate()
            add_message(chat_message, chat_messages)

            self.set_status(200);
            self.add_to_payload('message','message sent')

        except ShieldException, se:
            self.set_status(403, 'VALIDATION ERROR: %s' % (se));

        return self.render()

class LoginHandler(JSONMessageHandler):
    """Allows users to enter the chat room.  Does no authentication."""

    def prepare(self):
        self.headers = {'Content-Type': 'application/json'}

    def post(self, nickname):
        if len(nickname) != 0:

            user = find_list_item_by_nickname(nickname, users_online)
            if user == None :
                user=add_user(User(nickname=nickname), users_online)
                msg = ChatMessage(timestamp=int(time.time() * 1000), nickname='system',
                    message="%s has entered the room" % unquote(nickname), msgtype='system')
                add_message(msg, chat_messages)

                ## respond to the client our success
                self.set_status(200)
                self.set_cookie('nickname',nickname)
                self.add_to_payload('message',nickname + ' has entered the chat room')

            else:
                ## let the client know we failed because they didn't ask nice
                self.set_status(403, 'identity theft is a serious crime')

        else:
            ## let the client know we failed because they didn't ask nice
            self.set_status(403, 'missing nickname argument')

        self.set_cookies()
        return self.render()

    def delete(self, nickname):
        """ remove a user from the chat session"""
        if len(nickname) != 0:

            ## remove our user and alert others in the chat room
            user = find_list_item_by_nickname(nickname, users_online)

            if user != None:
                remove_user(user, users_online_list)
                msg = ChatMessage(timestamp=int(time.time() * 1000), nickname='system',
                   message='%s has left the room.' % nickname, msgtype='system')
                add_message(msg, chat_messages)

                ## respond to the client our success
                self.set_status(200)
                self.add_to_payload('message',nickname + ' has left the chat room')

            else:
                ## let the client know we failed because they didn't ask nice
                self.set_status(403, nicknmame + ' is not in the room')

        else:
            ## let the client know we failed because they didn't ask nice
            self.set_status(403, 'missing nickname argument')
        self.set_cookies()
        return self.render()

    def set_cookies(self):
        # Resolve cookies into multiline value
        cookie_vals = [c.OutputString() for c in self.cookies.values()]
        if len(cookie_vals) > 0:
            cookie_str = '\nSet-Cookie: '.join(cookie_vals)
            self.headers['Set-Cookie'] = cookie_str


project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
template_dir = os.path.join(project_dir, 'templates')

config = {
    'mongrel2_pair': ('ipc://run/mongrel2_send', 'ipc://run/mongrel2_recv'),
    'handler_tuples': [
        (r'^/$', ChatifyHandler),
        (r'^/feed$', FeedHandler),
        (r'^/login/(?P<nickname>.+)$', LoginHandler),
    ],
    'cookie_secret': '1a^O9s$4clq#09AlOO1!',
    'template_loader': load_jinja2_env(template_dir),
}


app = Brubeck(**config)
## this allows us to import the demo as a module for unit tests without running the server
if __name__ == "__main__":
    app.run()
