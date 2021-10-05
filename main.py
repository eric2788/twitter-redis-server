import asyncio
import time
from twitter_api import TwitterSpiders
from redis_api import initRedis, send_live_room_status
from redis.exceptions import RedisError
from typing import Dict


VERSION = 'v0.2'

started = set()
excepted = set()

listenMap: Dict[str, bool] = dict()

async def launch_server():
    redis = await initRedis()
    spiders = TwitterSpiders(redis)
    print(f'twitter-redis-server {VERSION} 成功啟動，正在監聽指令...')
    try:
        while True:
            time.sleep(10)
            channels = redis.pubsub_channels('twitter:*')
            subscribing = set()

            for room in channels:
                username = room.decode('utf-8').replace("twitter:", "")

                if username in excepted:
                    continue

                subscribing.add(username)
                
            listening = set(started)

            for to_listen in subscribing - listening:
                if to_listen in started:
                    continue
                started.add(to_listen)

            for to_stop in listening - subscribing:
                started.discard(to_stop)

            if listening.symmetric_difference(started):
                listening = started
                await spiders.refresh_stream(started)
    except RedisError as e:
        print(f'連接到 Redis 時出現錯誤: {e}')
        print(f'等待五秒後重連...')
        asyncio.sleep(5)
        await launch_server()


if __name__ == '__main__':
    asyncio.run(launch_server())