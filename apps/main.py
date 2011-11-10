#!/usr/bin/env python
from brubeck.templating import load_jinja2_env, Jinja2Rendering
from dictshield.document import Document
import brubeck
import gevent
import os
import sys
import time

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
chat_messages = []

## Our long polling interval
POLL_INTERVAL = 5

## Add a message to our in memory collection
def add_message(chat_message):
    ## use the servers current time as a key so the user can request only newer items after the initial load
    chat_messages.append(chat_message)
    ## we only need to store the most recent items
    if len(chat_messages) > LIST_SIZE:
        ## remove the first(oldest) element of the list
        del chatmessages[0]

## get new messages since a certain timestamp
def get_messages(since_timestamp):
    since_timestamp = float(since_timestamp)
    newer_chat_messages = ChatMessages()
    newer_chat_messages.timestamp = since_timestamp
    if(len(chat_messages) > 0):
        ## see if we have any newer messages
        last_message_timestamp = float(chat_messages[-1].timestamp)
        if since_timestamp < last_message_timestamp:
            ## loop through our messages only adding the newer ones
            for message in chat_messages:                
                if since_timestamp < float(message.timestamp):
                    newer_chat_messages.messages.append(message)
                    newer_chat_messages.timestamp = message.timestamp
    return newer_chat_messages

## A single message
class ChatMessage(EmbeddedDocument):
    timestamp =  FloatField(default=time.time)
    nickname = StringField(required=True, max_length=40)
    message = StringField(required=True)

## a collection of messages
class ChatMessages(Document):
    timestamp = FloatField(default=time.time)
    messages = ListField(EmbeddedDocumentField(ChatMessage))


class ChatifyHandler(WebMessageHandler, Jinja2Rendering):
    
    def get(self):
        # just start us up, it's all in the AJAX
        # self.set_body('Take five, %s!' % name)
        return self.render_template('base.html')

class JSONAddMessageHandler(JSONMessageHandler):
    def post(self):
        nickname = self.get_argument('nickname')
        message = self.get_argument('message')
        chat_message = ChatMessage(**{'nickname': nickname, 'message': message})
        try:
            chat_message.validate()
            add_message(chat_message)
            self.set_status(200);
            self.add_to_payload('message','message sent')
        except ShieldException, se:
            self.set_status('ERROR');
            self.add_to_payload('message','VALIDATION ERROR: %s' % (se))
        return self.render()

class JSONChatFeedHandler(JSONMessageHandler):
    def get(self):
        try:
            since_timestamp = float(self.get_argument('since_timestamp', 0))
        except Exception:
            since_timestamp = 0

        gevent.sleep(POLL_INTERVAL) # simple way to demo long polling :)
        self.set_status(200)
        self.add_to_payload('messages', get_messages(since_timestamp))
        self.headers= {'Content-Type': 'application/json'}
        return self.render()

project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
template_dir = os.path.join(project_dir, 'templates')
config = {
    'mongrel2_pair': ('ipc://run/mongrel2_send', 'ipc://run/mongrel2_recv'),
    'handler_tuples': [(r'^/$', ChatifyHandler),
                       (r'^/add', JSONAddMessageHandler),
                       (r'^/chatfeed', JSONChatFeedHandler)],
    'template_loader': load_jinja2_env(template_dir),
}


app = Brubeck(**config)
## this allows us to import the demo as a module for unit tests without running the server
print "project_dir: %s" % project_dir
print "template_dir: %s" % template_dir
if __name__ == "__main__":
    app.run()
