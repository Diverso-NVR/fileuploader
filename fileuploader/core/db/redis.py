import asyncio
from typing import Dict, Union

import aioredis
import ujson

from ..settings import settings


async def create_pool():
    global redis
    redis = await aioredis.create_redis_pool(settings.redis_url)


asyncio.run(create_pool())


async def close_redis():
    redis.close()
    await redis.wait_closed()


async def load_data(file_id: str) -> Dict[str, Union[str, int, None]]:
    file = await redis.get(file_id, encoding="utf-8")
    return ujson.loads(file)


async def dump_data(file_id: str, file_data: Dict[str, Union[str, int, None]]) -> None:
    await redis.set(
        file_id,
        ujson.dumps(file_data),
    )


async def remove_data(file_id: str) -> None:
    await redis.delete(file_id)
