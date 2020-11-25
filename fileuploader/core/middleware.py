from fastapi import Request
from fastapi.responses import JSONResponse

from .connections import get_user


async def authorization(request: Request, call_next):

    if request.url.path in [
        "/api/fileuploader/docs",
        "/api/fileuploader/redoc",
        "/api/fileuploader/openapi.json",
    ]:
        return await call_next(request)

    api_key = request.headers.get("key")
    if api_key is None:
        return JSONResponse(status_code=401, content={"message": "No API key provided"})

    user = await get_user(api_key)
    if not user:
        return JSONResponse(status_code=401, content={"message": "Invalid API key"})

    return await call_next(request)
