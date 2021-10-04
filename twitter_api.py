import threading
from typing import Dict, Generator
import twitter
import json
from twitter.error import TwitterError
from twitter.models import User
from redis import Redis
from twitter.ratelimit import EndpointRateLimit, RateLimit
from redis_api import send_live_room_status



def init_api():
    f = open('./config/config.json')
    config = json.load(f)
    return twitter.Api(**config['api'], sleep_on_rate_limit=True)

api = init_api()


class TwitterSpiders:

    REDIS: Redis = None

    def __init__(self, redis: Redis):
        self.redis = redis
        self.stream = None
        self.listening = []
        self.should_refresh = False

    def add_listen(self, user: str):
        self.listening.append(user)
        self.refresh_stream()

    def remove_listen(self, user: str):
        self.listening.remove(user)
        self.refresh_stream()

    def refresh_stream(self):
        self.stream.close()
        thread = threading.Thread(target=self.launch_stream)
        thread.start()

    def launch_stream(self):
        for data in api.GetStreamFilter(follow=self.listening):
            try:
                print(f'檢測到 {data["user"]["name"]} 有新動態，已成功發佈。')
                TwitterSpiders.REDIS.publish(f'twitter:{data["user"]["screen_name"]}', json.dumps(data))
            except TwitterError as e:
                print(f'追蹤推特用戶推文時出現錯誤: {e.message}')
            


class TwitterSpider:

    REDIS = None

    def __init__(self, user: str, username: str) -> None:
        self.user = user
        self.screen = username
        self.closed = True
        limit: RateLimit = api.rate_limit
        print(f'stream limit: {limit.get_limit(api.base_url+"/statuses/filter.json")._asdict}')


    def listen(self, stream: Generator[any, None, None]):
        while not self.closed:
            try:
                data = next(stream)
                print(f'檢測到 {self.screen} 有新推特，已成功發佈。')
                TwitterSpider.REDIS.publish(f'twitter:{self.screen}', json.dumps(data))
            except StopIteration:
                break
        stream.close()

    async def start(self):
        stream = api.GetStreamFilter(follow=[self.user])
        await send_live_room_status(self.screen, "started")
        self.closed = False
        self.thread = threading.Thread(target=self.listen, args=(stream, ))
        self.thread.start()    

    async def close(self):
        if self.closed:
            return
        self.closed = True
        await send_live_room_status(self.screen, "stopped")


user_caches: Dict[str, User] = dict()

async def get_user(screen_name: str):
    if screen_name in user_caches:
        return user_caches[screen_name]
    user = api.GetUser(screen_name=screen_name)
    user_caches[screen_name] = user
    return user
    
    
