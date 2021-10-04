import threading
from typing import Dict, Generator
import twitter
import json
from twitter.api import Api

from twitter.models import User
from redis_api import send_live_room_status



def init_api():
    f = open('./config/config.json')
    config = json.load(f)
    return twitter.Api(**config['api'])

api = init_api()


class TwitterSpider:

    REDIS = None

    def __init__(self, user: str, username: str) -> None:
        self.user = user
        self.screen = username
        self.closed = True


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
    
    
