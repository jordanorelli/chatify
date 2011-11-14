#!/usr/bin/env python
from brubeck.request_handling import Brubeck, JSONMessageHandler
from brubeck.templating import load_jinja2_env, Jinja2Rendering
from dictshield import fields
from dictshield.fields import EmbeddedDocument, ShieldException
from gevent.event import Event
import os
import time

## hold our messages in memory here, limit to last 20
LIST_SIZE = 50
users_online = []
chat_messages = []
new_message_event = Event()

## Our long polling interval
POLL_INTERVAL = 5

def add_message(chat_message):
    """Adds a message to our message history. A server timestamp is used to
    avoid sending duplicates."""
    chat_messages.append(chat_message)
    if len(chat_messages) > LIST_SIZE:
        chat_messages.pop(0)

def get_messages(since_timestamp=0):
    """get new messages since a certain timestamp"""
    return filter(lambda x: x.timestamp > since_timestamp,
                  chat_messages)

class ChatMessage(EmbeddedDocument):
    """A single message"""
    timestamp = fields.IntField(required=True)
    nickname = fields.StringField(required=True, max_length=40)
    message = fields.StringField(required=True)
    msgtype = fields.StringField(default='user',
                          choices=['user', 'error', 'system'])

    def __init__(self, *args, **kwargs):
        super(ChatMessage, self).__init__(*args, **kwargs)
        self.timestamp = int(time.time())

class ChatifyHandler(Jinja2Rendering):
    """Renders the chat interface template."""

    def get(self):
        return self.render_template('base.html')


class FeedHandler(JSONMessageHandler):
    """Handles poll requests from user; sends out queued messages."""

    def get(self):
        try:
            messages = get_messages(int(self.get_argument('since_timestamp', 0)))
        except ValueError as e:
            print str(e)
            messages = get_messages()

        if len(messages)==0:
            new_message_event.wait(POLL_INTERVAL)

        self.set_status(200)
        self.headers= {'Content-Type': 'application/json'}
        self.add_to_payload('messages', messages)
        return self.render()

    def post(self):
        nickname = self.get_argument('nickname')
        message = self.get_argument('message')
        chat_message = ChatMessage(**{'nickname': nickname, 'message': message})
        try:
            chat_message.validate()
            add_message(chat_message)

            new_message_event.set()
            new_message_event.clear()

            self.set_status(200);
            self.add_to_payload('message','message sent')

        except ShieldException, se:
            self.set_status(403, 'VALIDATION ERROR: %s' % (se));
            self.headers = {'Content-Type': 'application/json'}
        return self.render()

class LoginHandler(JSONMessageHandler):
    """Allows users to enter the chat room.  Does no authentication."""

    def post(self, nickname):
        if len(nickname) != 0:
            try:
                i = users_online.index(nickname)
            except ValueError:
                i = -1 # no match

            if i  == -1 :
                users_online.append(nickname)
                msg = ChatMessage(timestamp=int(time.time()), nickname='system',
                    message='%s has entered the room.' % nickname, msgtype='system')
                add_message(msg)

                ## respond to the client our success
                self.set_status(200)
                self.headers = {'Content-Type': 'application/json'}
                self.add_to_payload('message',nickname + ' has entered the chat room')

            else:
                ## let the client know we failed because they didn't ask nice
                self.set_status(403, 'identity theft is a serious crime')
                self.headers = {'Content-Type': 'application/json'}

        else:
            ## let the client know we failed because they didn't ask nice
            self.set_status(403, 'missing nickname argument')
            self.headers = {'Content-Type': 'application/json'}

        return self.render()

    def delete(self, nickname):
        """ remove a user from the chat session """
        if len(nickname) != 0:
            ## remove our user and alert others in the chat room
            try:
                i = users_online.index(nickname)
            except ValueError:
                i = -1 # no match

            if i > -1:
                users_online.pop(i)
                msg = ChatMessage(timestamp=int(time.time()), nickname='system',
                   message='%s has left the room.' % nickname, msgtype='system')
                add_message(msg)

                ## respond to the client our success
                self.set_status(200)
                self.set_status_message("ERROR")
                self.headers = {'Content-Type': 'application/json'}
                self.add_to_payload('message',nickname + ' has left the chat room')

            else:
                ## let the client know we failed because they didn't ask nice
                self.set_status(403, nicknmame + ' is not in the room')
                self.headers = {'Content-Type': 'application/json'}

        else:
            ## let the client know we failed because they didn't ask nice
            self.set_status(403, 'missing nickname argument')
            self.headers = {'Content-Type': 'application/json'}

        return self.render()


project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
template_dir = os.path.join(project_dir, 'templates')
config = {
    'mongrel2_pair': ('ipc://run/mongrel2_send', 'ipc://run/mongrel2_recv'),
    'handler_tuples': [
        (r'^/$', ChatifyHandler),
        (r'^/feed$', FeedHandler),
        (r'^/login/(?P<nickname>\w+)$', LoginHandler),
    ],
    'template_loader': load_jinja2_env(template_dir),
}


app = Brubeck(**config)
## this allows us to import the demo as a module for unit tests without running the server
if __name__ == "__main__":
    app.run()
