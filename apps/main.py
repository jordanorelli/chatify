#!/usr/bin/env python
from brubeck.request_handling import Brubeck, JSONMessageHandler
from brubeck.templating import load_jinja2_env, Jinja2Rendering
from brubeck.auth import authenticated
from dictshield import fields
from dictshield.document import Document
from dictshield.fields import EmbeddedDocument, ShieldException
from gevent.event import Event
from urllib import unquote
import os
import time
from gevent import Greenlet
import functools
import logging

## add redis support if available
## redis also handles persistance and synching all brubeck chatify instances
## without redis only a single instance can be run
using_redis = False
try:
    import redis
    import json
    using_redis = True
except Exception:
    logging.info("redis module not found (single instance mode: using in memory buffer)")
    pass


## hold our messages in memory here, limit to last 50
## persistance is handled by redis, or not at all
LIST_SIZE = 50
users_online = []
chat_messages = []
new_message_event = Event()

## Our long polling interval
POLLING_INTERVAL = 30

## How old a user must be in seconds to kick them out of the room
USER_TIMEOUT = 60
##
## our redis channel listeners
##

def redis_new_chat_messages_listener(redis_server):
    """listen to redis for when new messages are published"""
    while True:
        msg = redis_new_chat_messages.next()
        ## just hook into our existing way for now
        ## a bit redundant but allows server to be run without redis
        logging.info("new chat message subscribed to: %s" % msg['data'])
        list_add_chat_message(ChatMessage(**json.loads(msg['data'])), chat_messages)

# we  don't need this anymore since we use expire on the user key
#def redis_new_users_listener(redis_server):
#    """listen to redis for when new users are published"""
#    while True:
#        msg = redis_new_users.next()
#        ## just hook into our existing way for now
#        ## a bit redundant but allows server to be run without redis
#        logging.info("new user subscribed to: %s" % msg['data'])
#        list_add_user(User(**json.loads(msg['data'])), users_online)

# we don't need this anymore since we use expire on the user key
#def redis_remove_users_listener(redis_server):
#    """listen to redis for when remove user messages are published"""
#    while True:
#        msg = redis_remove_users.next()
#        ## just hook into our existing way for now
#        ## a bit redundant but allows server to be run without redis
#        logging.info("new remove message subscribed to: %s" % msg['data'])
#        list_remove_user(User(**json.loads(msg['data'])), users_online)

# we don't need this anymore since we use expire on the user key
#def redis_update_users_timestamp_listener(redis_server):
#    """listen to redis for when updated users timestamp are published"""
#    while True:
#        msg = redis_update_users_timestamp.next()
#        ## just hook into our existing way for now
#        ## a bit redundant but allows server to be run without redis
#        logging.info("new update user timestamp subscribed to: %s" % msg['data'])
#        list_update_user_timestamp(User(**json.loads(msg['data'])), users_online)

##
## Methods to add a chat message
##

def add_chat_message(message):
    """ the xxx_add_chat_message wrapper, uses redis by default if possible"""
    if using_redis:
        redis_add_chat_message(message, redis_server)
    else:
        list_add_chat_message(message, chat_messages)

def list_add_chat_message(chat_message, chat_messages_list):
    """Adds a message to our message history. A server timestamp is used to
    avoid sending duplicates."""
    chat_messages_list.append(chat_message)

    if len(chat_messages_list) > LIST_SIZE:
        chat_messages_list.pop(0)

    # alert our polling clients
    new_message_event.set()
    new_message_event.clear()

def redis_add_chat_message(chat_message, redis_server):
    """adds a message to the redis server and publishes it"""
    data = chat_message.to_json()
    logging.info(data)

    redis_server.rpush('add_chat_messages', data)
    redis_server.publish('add_chat_messages', data)

def get_messages(chat_messages_list, since_timestamp=0):
    """get new messages since a certain timestamp"""
    return filter(lambda x: x.timestamp > since_timestamp,
                  chat_messages)

##
## Methods to add a user
##

def add_user(user):
    """add a user to our online users. Timestamp used to determine freshness"""
    """ the xxx_add_user_message wrapper, uses redis by default if possible"""
    if using_redis:
        redis_add_user(user, redis_server)
    else:
        list_add_user(user, users_online)

def list_add_user(user, users_online_list):
    """add a user to our online users. Timestamp used to determine freshness"""
    users_online_list.append(user)

def redis_add_user(user, redis_server):
    """adds a user to the redis server and publishes it"""

    data = user.to_json()
    logging.info(data)

    #no more record for tiemstamp, expire key instead
    # add our nickname to a set orderes by timestamp to be able to quickly purge
    # redis_server.zadd("user_timestamps",user.nickname, user.timestamp)
    # add our user object to a simple set, keyed by nickname
    redis_server.set('users:%s' % user.nickname, data)
    redis_server.expire('users:%s' % user.nickname, USER_TIMEOUT)
    # no longer needed, not in memory anymore i using redis
    # publish our new user
    #redis_server.publish('add_users', data)
    #logging.info("new user added and published: %s" % data)

##
## Methods to remove a user
##
def remove_user(user):
    """remove a user from our users_online"""
    """ the xxx_remove_user wrapper, uses redis by default if possible"""
    if using_redis:
        redis_remove_user(user, redis_server)
    else:
        list_remove_user(user, users_online)

def list_remove_user(user, users_list):
    """remove a user from a list"""
    for i in range(len(users_list)):
        if users_list[i].nickname == user.nickname:
            del users_list[i]
            break

def redis_remove_user(user, redis_server):
    """removes a user from the redis server and publishes it"""

    data = user.to_json()
    logging.info(data)
    # no more timestamp record
    # remove our users timestamp
    # affected = redis_server.zrem('user_timestamps',user.nickname)
    # logging.info("removed user timestamp(%d): %s" % (affected, user.nickname))
    # remove our user 
    affected = redis_server.expire('users:%s' % user.nickname, 0)
    logging.info("removed user(%d): %s" % (affected, data))
    redis_server.publish('remove_users', data)

##
## Update our users timestamp methods
##

def update_user_timestamp(user):
    """ the xxx_update_user_timestamp wrapper, uses redis by default if possible"""
    user.timestamp = int(time.time())
    if using_redis:
        return redis_update_user_timestamp(user, redis_server)
    else:
        return list_update_user_timestamp(user, users_online)


def list_update_user_timestamp(user, target_list):
    """updates the timestamp on the user to avoid expiration"""
    usr = find_user_by_nickname(user.nickname)
    if usr != None:
        usr.timestamp = user.timestamp
    return usr

def redis_update_user_timestamp(user, redis_server):
    """timestamps our active user and publishes the changes"""
    data = user.to_json()
    #logging.info("updating users timestamp: %s" % data)
    logging.info("updating users key expiration(%d): %s" % (USER_TIMEOUT, user.nickname))
    redis_server.expire("users:%s" % user.nickname, USER_TIMEOUT)
    # why bother with any of this, just update expiration above
    # update our timestamp ordered set
    # redis_server.zadd("update_users_timestamp", user.nickname, user.timestamp)
    # update the object ourself
    # redis_server.set("users:%s" % user.nickname, data)
    # publish
    # redis_server.publish("update_users_timestamp", data)
    return user

def find_user_by_nickname(nickname):
    """returns a user by nickname, trying redis first"""
    if using_redis:
        user = redis_find_user_by_nickname(nickname, redis_server)
    else:
        user = list_find_user_by_nickname(nickname, users_online)
    return user

def list_find_user_by_nickname(nickname, target_list):
    """returns the first list item matching a nickname"""
    items = filter(lambda x: x.nickname == nickname,
                   target_list)
    if len(items)==0:
        return None
    else:
        return items[0]

def redis_find_user_by_nickname(nickname, redis_server):
    """returns the user by nickname"""
    data = redis_server.get("users:%s" % nickname)
    logging.info(data)
    if data != None:
        logging.info("found user by nickname: %s" % data)
        return User(**json.loads(data))
    else:
        logging.info("unable to find user by nickname: %s" % nickname)
        return None

def list_find_user_by_nickname(nickname, users_list):
    """returns the first list item matching a nickname"""
    items = filter(lambda x: x.nickname == nickname,
                   users_list)
    if len(items)>0:
        user = items[0]
    else:
        user = None
    return user

##
## Check online user methods
##

def check_users_online():
    """check for expired users and send a message they left the room"""
    before_timestamp = int((time.time()) - (USER_TIMEOUT))

    if using_redis:
        # we let the user expire by key if using redis
        pass
        #redis_check_users_online(before_timestamp, redis_server)
    else:
        list_check_users-online(before_timestamp, users_online)

    ## setup our next check
    g = Greenlet(check_users_online)
    g.start_later(POLLING_INTERVAL)

def list_check_users_online(before_timestamp, users_list):
    """check for expired users and send a message they left the room"""
    expired_users = filter(lambda x: x.timestamp <= before_timestamp,
                   users_list)
    for user in expired_users:
        msg = ChatMessage(nickname='system', message="%s can not been found in the room" % user.nickname);

        add_chat_message(msg)
        remove_user(user)

def redis_check_users_online(before_timestamp, redis_server):
    """check for expired users and send a message they left the room"""
    expired_users = redis_server.zrange("user_timestamps",0, before_timestamp)

    for nickname in expired_users:
        user = User(**json.loads(redis_server.get("users:%s" % nickname)))
        msg = ChatMessage(nickname='system', message="%s can not been found in the room" % user.nickname);

        add_chat_message(msg)
        remove_user(user)

class User(Document):
    """a chat user"""
    timestamp = fields.IntField(required=True)
    nickname = fields.StringField(required=True, max_length=40)

    def __init__(self, *args, **kwargs):
        super(User, self).__init__(*args, **kwargs)
        # seconds is enough here, we need an int
        self.timestamp = int(time.time())

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
        return self.render_template('base.html')

class ChatifyJSONMessageHandler(JSONMessageHandler):
    """our JSON message handlers base class"""

    def prepare(self):
        """get our user from the request and set to self.current_user"""

        try:
            nickname = self.get_argument('nickname')
            user = find_user_by_nickname(nickname)
	    if user != None:
                self.current_user = update_user_timestamp(user)

        except Exception:
            self.current_user = None

    def get_current_user(self):
        """return  self.current_user set in self.prepare()"""
        return self.current_user


class FeedHandler(ChatifyJSONMessageHandler):
    """Handles poll requests from user; sends out queued messages."""
 
    def _get_messages(self):
        """checks for new messages"""

        try:
            messages = get_messages(chat_messages, int(self.get_argument('since_timestamp', 0)))

        except ValueError as e:
            messages = get_messages(chat_messages)

        return messages

    @authenticated
    def get(self):
        """gets any recent messages, or waits for new ones to appear"""

        messages = self._get_messages()

        if len(messages)==0:
            # we don't have any messages so sleep for a bit
            new_message_event.wait(POLLING_INTERVAL)

            # done sleeping or woken up
            #check again and return response regardless
            messages = self._get_messages()

        self.set_status(200)
        self.add_to_payload('messages', messages)

        return self.render()

    @authenticated
    def post(self):

        nickname = unquote(self.get_argument('nickname'))
        message = unquote(self.get_argument('message'))
        logging.info("%s: %s" % (nickname, message))
        msg = ChatMessage(**{'nickname': nickname, 'message': message})

        try:
            msg.validate()
            add_chat_message(msg)

            self.set_status(200);
            self.add_to_payload('message','message sent')

        except ShieldException, se:
            self.set_status(403, 'VALIDATION ERROR: %s' % (se));

        return self.render()

class LoginHandler(ChatifyJSONMessageHandler):
    """Allows users to enter the chat room.  Does no authentication."""

    def post(self, nickname):
        nickname = unquote(nickname)
        if len(nickname) != 0:

            user = find_user_by_nickname(nickname)
            if user == None :
                user=add_user(User(nickname=nickname))
                msg = ChatMessage(timestamp=int(time.time() * 1000), nickname='system',
                    message="%s has entered the room" % nickname, msgtype='system')
                
                add_chat_message(msg)
                
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

        self.convert_cookies()
        return self.render()

    def delete(self, nickname):
        """ remove a user from the chat session"""
        nickname = unquote(nickname)
        if len(nickname) != 0:

            ## remove our user and alert others in the chat room
            user = find_user_by_nickname(nickname)

            if user != None:
                remove_user(user)
                msg = ChatMessage(timestamp=int(time.time() * 1000), nickname='system',
                   message='%s has left the room.' % nickname, msgtype='system')

                add_chat_message(msg)

                ## respond to the client our success
                self.set_status(200)
                self.add_to_payload('message',unquote(nickname) + ' has left the chat room')

            else:
                ## let the client know we failed because they were not found
                self.set_status(403, 'Authentication failed')

        else:
            ## let the client know we failed because they didn't ask nice
            self.set_status(403, 'missing nickname argument')
        self.convert_cookies()
        return self.render()

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

    if using_redis:
        try:
            ## attach to our redis server
            ## we do all the setup here, so if we fail our flag is set properly
            redis_server = redis.Redis(host='localhost', port=6379, db=0)
            
            redis_client1 = redis_server.pubsub()
            redis_client1.subscribe('add_chat_messages')
            redis_new_chat_messages = redis_client1.listen()

            #no more in memory buffer for users if we are using redis
            #redis_client2 = redis_server.pubsub()
            #redis_client2.subscribe('add_users')
            #redis_new_users = redis_client2.listen()

            #redis_client3 = redis_server.pubsub()
            #redis_client3.subscribe('remove_users')
            #redis_remove_users = redis_client3.listen()

            #redis_client4 = redis_server.pubsub()
            #redis_client4.subscribe('update_users_timestamp')
            #redis_update_users_timestamp = redis_client4.listen()

            logging.info("succesfully connected to redis")
            try:
                ## fill the in memory buffer with redis data here
                msgs = redis_server.lrange("chat_messages", -1 * LIST_SIZE, -1)
                i = 0
                for msg in msgs:
                    chat_messages.append(ChatMessage(**json.loads(msg)))
                    i += 1
                logging.info("loaded chat_messages memory buffer (%d)" % i)
            except Exception, e:
                logging.info("failed to load messages from redis: %s" % e)

            # No more local user with redis
            #try:
            #    ## fill the in memory buffer with redis data here
            #    user_keys = redis_server.keys("users:*")
            #    i = 0
            #    for user_key in user_keys:
            #        usr = redis_server.get(user_key)
            #        users_online.append(User(**json.loads(usr)))
            #        i += 1
            #    logging.info("loaded users_online memory buffer (%d)" % i)
            #except Exception, e:
            #    logging.info("failed to users_online from redis: %s" % e)

                
            ## spawn out the process to listen for new messages in redis
            g1 = Greenlet(redis_new_chat_messages_listener, redis_server)
            g1.start()

            ## we don't really need these, we are suing redis soley for users
            ## spawn out the process to listen for new messages in redis
            #g2 = Greenlet(redis_new_users_listener, redis_server)
            #g2.start()

            ## spawn out the process to listen for new messages in redis
            #g3 = Greenlet(redis_remove_users_listener, redis_server)
            #g3.start()

            ## spawn out the process to listen for new messages in redis
            #g4 = Greenlet(redis_update_users_timestamp_listener, redis_server)
            #g4.start()

            logging.info("started redis listener")
        except Exception:
            using_redis = False
            logging.info("unable to connect to redis, make sure it is running (single instance mode: using in memory buffer)")


    ## spawn out online user checker to timeout users after inactivity
    ## only if not using redis (really online_users should be ignored everywhere)
    if using_redis == False:
        g = Greenlet(check_users_online)
        g.start_later(POLLING_INTERVAL)

    ## start our server to handle requests
    app.run()
