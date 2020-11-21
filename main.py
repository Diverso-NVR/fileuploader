import sys
import logging
import uvicorn
import redis
import os
import pickle
from fastapi import FastAPI, middleware
from starlette.middleware.base import BaseHTTPMiddleware
from middleware import authorization
from routes import routes
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

r = redis.Redis(host="localhost", port=6379, db=0)


TOKEN_PATH = "creds/tokenDrive.pickle"
CREDS_PATH = "creds/credentials.json"
SCOPES = "https://www.googleapis.com/auth/drive"


def creds_generate():
    creds = None
    # if you do not have creds
    # flow = InstalledAppFlow.from_client_secrets_file(CREDS_PATH, SCOPES)
    # creds = flow.run_local_server(port=0)
    # with open(TOKEN_PATH, "wb") as token:
    #     pickle.dump(creds, token)
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, "rb") as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            return creds
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
            return creds
        with open(TOKEN_PATH, "wb") as token:
            pickle.dump(creds, token)
    else:
        return creds


creds = creds_generate()

if __name__ == "__main__":
    app = FastAPI()
    app.include_router(routes.router)
    app.add_middleware(
        BaseHTTPMiddleware, dispatch=authorization
    )  # применяется ко всем запросам

    logging.basicConfig(
        stream=sys.stdout, level=logging.INFO, format="%(asctime)s - %(message)s"
    )

    uvicorn.run(app, host="0.0.0.0", port=5005)

    # logging.basicConfig(
    #     filename="logging/logs.log",
    #     filemode="a",
    #     format="%(asctime)s - %(message)s",
    #     level=logging.INFO,
    # )


# можно в гугл функциях выдавать нормальные исключения
# зачем писать __init__.py

# для прода
# os.environ['DB_URL'] -- задать, server_path тоже
# добавить слеши  в именах в папках
# заменить получение секретного ключа
#
