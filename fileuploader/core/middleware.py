from fastapi import Request
from fastapi.responses import JSONResponse

from .connections import db_connect


async def authorization(request: Request, call_next):
    if request.url.path in ["/docs", "/redoc", "/openapi.json"]:
        return await call_next(request)

    api_key = request.headers.get("key")
    if api_key is None:
        return JSONResponse(status_code=401, content={"message": "No API key provided"})

    async with db_connect() as conn:
        user = await conn.fetchrow(
            "SELECT id, email FROM users WHERE api_key = $1", api_key
        )
    if not user:
        return JSONResponse(status_code=401, content={"message": "Invalid API key"})

    return await call_next(request)
