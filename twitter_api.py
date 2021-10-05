import asyncio
from json.decoder import JSONDecodeError
from typing import Dict
import json
from redis import Redis
from tweepy.errors import TweepyException
from tweepy.models import Status
from redis_api import send_live_room_status
import tweepy

class TweetStream(tweepy.Stream):
    
    def on_connect(self):
        self.closed=False
        print(f'推特串流成功啟動。')

    def set_data_handler(self, func):
        self.func = func

    def on_closed(self, response):
        print(f'推特串流已關閉: {response}')
        self.closed=True

    async def wait_until_closed(self):
        while not self.closed:
            await asyncio.sleep(1)
        
    def on_connection_error(self):
        print(f'連接錯誤')

    def on_data(self, raw_data):
        if not self.func:
            return
        self.func(raw_data)

def init_api():
    f = open('./config/config.json')
    config = json.load(f)
    return tweepy.Client(**config['api'], wait_on_rate_limit=True)

def init_stream():
    f = open('./config/config.json')
    config = json.load(f)
    auth = config['api']
    del auth['bearer_token']
    return TweetStream(**auth, daemon=True)

api = init_api()
stream = init_stream()


class TwitterSpiders:

    def __init__(self, redis: Redis):
        self.redis = redis
        self.thread = None
        self.stream = None
        self.listening = []
        stream.set_data_handler(self.on_data)

    async def refresh_stream(self, listening=[]):
        print(f'正在刷新串流...')
        await self.close_stream()
        if not listening: # 空值
            return
        followers = []
        for username in listening:
            user = await user_lookup(username)
            if user == None:
                continue
            followers.append(str(user.id))
            print(f'即將監控 {user.name} 的推文')
        try:
            self.thread = stream.filter(follow=followers, threaded=True)
            for username in listening:
                await send_live_room_status(username, "started")
            self.listening = listening
            print(f'推特監控已啟動')
        except TweepyException as e:
            print(f'追蹤推特用戶推文時出現錯誤: {e.message}')

    def on_data(self, raw_data):
        try:
            data = json.loads(raw_data.decode('utf-8'))
            if 'delete' in data:
                return # skip delete post 
            print(f'檢測到 {data["user"]["name"]} 有新動態，已成功發佈。')
            self.redis.publish(f'twitter:{data["user"]["screen_name"]}', json.dumps(data))
        except {Exception, ValueError} as e:
            print(f'檢測推文時出現錯誤: {e}')

    async def close_stream(self):
        if not self.thread:
            return
        stream.disconnect()
        print(f'等待推特監控關閉...')
        await stream.wait_until_closed()
        for latest_listen in self.listening:
            await send_live_room_status(latest_listen, "stopped")
        print(f'推特監控已關閉')
        self.thread = None
        self.listening = []

user_caches: Dict[str, any] = dict()

async def user_lookup(screen_name: str):
    if screen_name in user_caches:
        return user_caches[screen_name]
    [data, include, error, meta] = api.get_user(username=screen_name)
    if error:
        print(f'請求用戶 {screen_name} 時出現錯誤: {error}')
        return None
    user_caches[screen_name] = data
    return data
