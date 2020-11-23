import asyncio

import aioredis
import asyncpg
from contextlib import asynccontextmanager

from .settings import settings


async def create_pool():
    global redis
    redis = await aioredis.create_redis_pool("redis://localhost:6379")


asyncio.run(create_pool())


async def close_redis():
    redis.close()
    await redis.wait_closed()


@asynccontextmanager
async def db_connect():
    conn = await asyncpg.connect(settings.db_url)
    try:
        yield conn
    finally:
        await conn.close()
