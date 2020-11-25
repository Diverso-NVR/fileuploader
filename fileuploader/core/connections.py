import asyncio

import aioredis
import asyncpg
from contextlib import asynccontextmanager

from .settings import settings


async def create_pool():
    global redis
    redis = await aioredis.create_redis_pool(settings.redis_url)


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


async def get_user(api_key: str) -> asyncpg.Record:
    async with db_connect() as conn:
        return await conn.fetchrow(
            "SELECT id, email FROM users WHERE api_key = $1", api_key
        )


async def get_online_room(name: str) -> asyncpg.Record:
    async with db_connect() as conn:
        return await conn.fetchrow(
            "SELECT id, name, drive FROM online_rooms WHERE name = $1", name
        )
