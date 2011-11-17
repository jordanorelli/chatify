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
from gevent import Greenlet

## hold our messages in memory here, limit to last 20
LIST_SIZE = 50
users_online = []
chat_messages = []
new_message_event = Event()

## Our long polling interval
POLLING_INTERVAL = 30

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

def timestamp_active_user(nickname, target_list):
    """updates the timestamp on the user to avoid expiration"""
    user = find_list_item_by_nickname(nickname, target_list)
    if user != None:
        user.timestamp = int(time.time() * 1000)
    else:
        raise ValueError("no such user in room")

def find_list_item_by_nickname(nickname, target_list):
    """returns the first list item matching a nickname"""
    items = filter(lambda x: x.nickname == nickname,
                   target_list)
    if len(items)==0:
        return None
    else:
        return items[0]

def check_users_online(users_list, chat_messages_list):
    """check for expired users and send a message they left the room"""
    since_timestamp = (time.time() * 1000) - (USER_TIMEOUT * 1000)

    print "checking online users to purge expired"

    users = filter(lambda x: x.timestamp <= since_timestamp,
                   users_list)
    for user in users:
        add_message(ChatMessage(nickname='system', message="%s can not been found in the room" % user.nickname),
                    chat_messages_list)
        remove_user(user, users_online)

    ## setup our next check
    g = Greenlet(check_users_online, users_online, chat_messages)
    g.start_later(POLLING_INTERVAL)

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
        return self.render_template('base.html', context=context)

class FeedHandler(JSONMessageHandler):
    """Handles poll requests from user; sends out queued messages."""

    def prepare(self):
        self.headers = {'Content-Type': 'application/json'}

    def check_nickname(self):
        """makes sure we are still an active user and updates our timestamp"""
        try:
            nickname = self.get_argument('nickname')
            timestamp_active_user(nickname, users_online)
        except:
            self.set_status(403, 'session is expired')
            raise ValueError("nickname empty or not active")

    def get_messages(self):
        """checks for new messages"""
        try:
            messages = get_messages(chat_messages, int(self.get_argument('since_timestamp', 0)))

        except ValueError as e:
            messages = get_messages(chat_messages)

        return messages


    def get(self):
        """gets any recent messages, or waits for new ones to appear"""
        try:
            self.check_nickname()
        except ValueError, er:
            print er.message
            return self.render()        

        messages = self.get_messages()

        if len(messages)==0:
            # we don't have any messages so sleep for a bit
            new_message_event.wait(POLLING_INTERVAL)
            # done sleeping or woken up
            #check again and return response regardless
            messages = self.get_messages()

        self.set_status(200)
        self.add_to_payload('messages', messages)

        return self.render()

    def post(self):
        try:
            self.check_nickname()
        except:
            return self.render()

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
        nickname = unquote(nickname)
        if len(nickname) != 0:

            user = find_list_item_by_nickname(nickname, users_online)
            if user == None :
                user=add_user(User(nickname=nickname), users_online)
                msg = ChatMessage(timestamp=int(time.time() * 1000), nickname='system',
                    message="%s has entered the room" % nickname, msgtype='system')
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
        nickname = unquote(nickname)
        if len(nickname) != 0:

            ## remove our user and alert others in the chat room
            user = find_list_item_by_nickname(nickname, users_online)

            if user != None:
                remove_user(user, users_online)
                msg = ChatMessage(timestamp=int(time.time() * 1000), nickname='system',
                   message='%s has left the room.' % nickname, msgtype='system')
                add_message(msg, chat_messages)

                ## respond to the client our success
                self.set_status(200)
                self.add_to_payload('message',unquote(nickname) + ' has left the chat room')

            else:
                ## let the client know we failed because they were not found
                self.set_status(403, 'session is expired')

        else:
            ## let the client know we failed because they didn't ask nice
            self.set_status(403, 'missing nickname argument')
        self.set_cookies()
        return self.render()

    def set_cookies(self):
        """Resolve cookies into multiline value"""
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

    ## spawn out online user checker to timeout users after inactivity
    g = Greenlet(check_users_online, users_online, chat_messages)
    g.start_later(POLLING_INTERVAL)
    
    ## start our server to handle requests
    app.run()
