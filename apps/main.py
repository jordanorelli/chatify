#!/usr/bin/env python
from brubeck.templating import load_jinja2_env, Jinja2Rendering
from dictshield.document import Document
import brubeck
import gevent
import os
import sys
import time
from gevent.event import Event
from brubeck.request_handling import(
    Brubeck, JSONMessageHandler,
    WebMessageHandler
)
from dictshield.fields import(
    StringField, IntField,
    FloatField, ListField,
    EmbeddedDocumentField, EmbeddedDocument,
    ShieldException
)

## hold our messages in memory here, limit to last 20
LIST_SIZE = 20
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
        chat_message.pop(0)

def get_messages(since_timestamp=0):
    """get new messages since a certain timestamp"""
    messages = filter(lambda x: x.timestamp > since_timestamp,
                      chat_messages)
    print "messages since %f: %r" % (since_timestamp,
                                     [(repr(m), m.timestamp)
                                      for m in messages])
    return messages

class ChatMessage(EmbeddedDocument):
    """A single message"""
    timestamp = IntField(required=True)
    nickname = StringField(required=True, max_length=40)
    message = StringField(required=True)
    msgtype = StringField(default='user',
                          choices=['user', 'error', 'system'])

    def __init__(self, *args, **kwargs):
        super(ChatMessage, self).__init__(*args, **kwargs)
        self.timestamp = int(time.time())
        print "%f: %s: %s" % (self.timestamp, self.nickname, self.message)

    def __repr__(self):
        return '<ChatMessage: %s>' % self.message


class ChatifyHandler(WebMessageHandler, Jinja2Rendering):
    """Renders the chat interface template."""

    def get(self):
        # just start us up, it's all in the AJAX
        # self.set_body('Take five, %s!' % name)
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
            self.set_status('ERROR');
            self.add_to_payload('message','VALIDATION ERROR: %s' % (se))
        return self.render()

class LoginHandler(JSONMessageHandler):
    """Allows users to enter the chat room.  Does no authentication."""

    def post(self):
        nickname = self.get_argument('nickname')
        users_online.append(nickname)
        self.set_status(200)
        msg = ChatMessage(timestamp=int(time.time()), nickname='system',
            message='%s has entered the room.' % nickname, msgtype='system')
        print repr(msg)
        add_message(msg)
        return self.render()


project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
template_dir = os.path.join(project_dir, 'templates')
config = {
    'mongrel2_pair': ('ipc://run/mongrel2_send', 'ipc://run/mongrel2_recv'),
    'handler_tuples': [
        (r'^/$', ChatifyHandler),
        (r'^/feed$', FeedHandler),
        (r'^/login$', LoginHandler),
    ],
    'template_loader': load_jinja2_env(template_dir),
}


app = Brubeck(**config)
## this allows us to import the demo as a module for unit tests without running the server
if __name__ == "__main__":
    app.run()
