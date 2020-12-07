import asyncpg
from contextlib import asynccontextmanager

from ..settings import settings


@asynccontextmanager
async def db_connect():
    conn = await asyncpg.connect(settings.psql_url)
    try:
        yield conn
    finally:
        await conn.close()


async def get_user(api_key: str) -> asyncpg.Record:
    async with db_connect() as conn:
        return await conn.fetchrow(
            "SELECT id, email FROM users WHERE api_key = $1", api_key
        )


async def get_room(name: str) -> asyncpg.Record:
    async with db_connect() as conn:
        room = await conn.fetchrow(
            "SELECT id, name, drive FROM online_rooms WHERE name = $1", name
        )
        if not room:
            room = await conn.fetchrow(
                "SELECT id, name, drive FROM rooms WHERE name = $1", name
            )

    return room
