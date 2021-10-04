import asyncio
from logging import error
import time
import twitter
from twitter_api import TwitterSpider, get_user
from redis_api import initRedis, send_live_room_status
from redis.exceptions import RedisError
from typing import Dict
import threading 


VERSION = 'v0.1'

started = set()
excepted = set()

listenMap: Dict[str, bool] = dict()
    

async def start_listen(username: str):
    try:
        user = await get_user(username)
        spider = TwitterSpider(user.id_str, username)
        await spider.start()
        print(f'成功啟動追蹤 {user.name} 的推特。')
        listenMap[username] = True
        while username in listenMap and listenMap[username] == True:
            await asyncio.sleep(1)
        await spider.close()
        print(f'已停止追蹤 {user.name} 的推特。')
        del listenMap[username]
    except twitter.error.TwitterError as e:
        print(f'獲取 {username} 的 Twitter ID 時 出現錯誤: {e.message}')
        await send_live_room_status(username, "error")
        excepted.add(username)

def run_thread(username: str):
    loop = asyncio.new_event_loop()
    loop.run_until_complete(start_listen(username))
    loop.close()

def stop_listen(username: str):
    listenMap[username] = False

async def launch_server():
    redis = await initRedis()
    TwitterSpider.REDIS = redis
    print(f'twitter-redis-server {VERSION} 成功啟動，正在監聽指令...')
    try:
        while True:
            time.sleep(1)
            channels = redis.pubsub_channels('twitter:*')
            subscribing = set()

            for room in channels:
                username = room.decode('utf-8').replace("twitter:", "")

                if username in excepted:
                    continue

                subscribing.add(username)
                
            listening = set(listenMap.keys())

            for to_listen in subscribing - listening:

                if to_listen in started:
                    continue

                thread = threading.Thread(target=run_thread, args=(to_listen, ))
                thread.start()
                started.add(to_listen)

            for to_stop in listening - subscribing:
                stop_listen(to_stop)
                started.discard(to_stop)
            
    except RedisError as e:
        print(f'連接到 Redis 時出現錯誤: {e}')
        print(f'等待五秒後重連...')
        asyncio.sleep(5)
        await launch_server()


if __name__ == '__main__':
    asyncio.run(launch_server())