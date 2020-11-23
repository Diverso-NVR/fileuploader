from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.openapi.utils import get_openapi

from core.connections import close_redis


def create_app():
    from core.settings import create_logger

    create_logger()

    from fastapi import FastAPI

    app = FastAPI(root_path="/api/fileuploader")

    from core.routes import router

    app.include_router(router)

    from core.middleware import authorization

    app.add_middleware(BaseHTTPMiddleware, dispatch=authorization)

    return app


app = create_app()


@app.on_event("shutdown")
async def shutdown_event():
    await close_redis()


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="Fileuploader",
        version="1.0.0",
        description="API to upload videos to NVR Google Drive",
        routes=app.routes,
    )
    openapi_schema["info"]["x-logo"] = {
        "url": "https://avatars2.githubusercontent.com/u/64712541?s=200&v=4"
    }

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=5500)
