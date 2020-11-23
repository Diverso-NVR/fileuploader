from fastapi import Request, Response
from fastapi.responses import JSONResponse

from .connections import db_connect


async def authorization(request: Request, call_next):
    if request.url.path in ["/docs", "/redoc", "/openapi.json"]:
        return await call_next(request)

    api_key = request.headers.get("key")
    if api_key is None:
        return JSONResponse(status_code=401, content={"message": "No API key provided"})

    response = await check_key(api_key)
    if not response.status_code == 200:
        return response

    return await call_next(request)


async def check_key(key: str):
    async with db_connect() as conn:
        user = await conn.fetchrow(
            "SELECT id, email FROM users WHERE api_key = $1", key
        )

    if not user:
        return JSONResponse(status_code=401, content={"message": "Invalid API key"})

    return Response(status_code=200)
