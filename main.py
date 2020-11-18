import sys
import logging
import uvicorn
from typing import List
from fastapi import FastAPI, Request, middleware
from starlette.middleware.base import BaseHTTPMiddleware
from middleware import authorization
from google_functions import creds_generate
from routes import routes







if __name__ == "__main__":
    app = FastAPI()
    app.include_router(routes.router)
    app.add_middleware(BaseHTTPMiddleware, dispatch=authorization) #применяется ко всем запросам

    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format="%(asctime)s - %(message)s"
    )
    creds_generate()

    uvicorn.run(app, host="0.0.0.0", port=5005)

    # logging.basicConfig(
    #     filename="logging/logs.log",
    #     filemode="a",
    #     format="%(asctime)s - %(message)s",
    #     level=logging.INFO,
    # )
    

# асинхронное удаление хз как сделать
# зачем писать __init__.py

# для прода
# os.environ['DB_URL'] -- задать
# добавить слеши  в именах в папках
# заменить получение секретного ключа
