from starlette.middleware.base import BaseHTTPMiddleware

from core.connections import close_redis


def create_app():
    from core.settings import create_logger

    create_logger()

    from fastapi import FastAPI

    app = FastAPI()

    from core.routes import router

    app.include_router(router)

    from core.middleware import authorization

    app.add_middleware(BaseHTTPMiddleware, dispatch=authorization)

    return app


app = create_app()


@app.on_event("shutdown")
async def shutdown_event():
    await close_redis()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=5500)
