import os
import logging
from fastapi import FastAPI, Request, HTTPException, Response



DATABASE_ADRESS = os.environ.get("DB_URL")



async def authorization(request: Request, call_next):
    token = request.headers.get('Token', '')
    api_key = request.headers.get('key', '')

    response = await check_jwt_token_and_key(token, api_key)
    if not response.status_code == 200:
        return response
        
    response = await call_next(request)
    return response

async def check_jwt_token_and_key(token: str, key: str):
    return Response("delete in prod", status_code=200)
    # как получить secret key?
    if token:
        try:
            data = jwt.decode(token, SECRET_KEY)
            conn = await asyncpg.connect(DATABASE_ADRESS)
            user = await conn.fetchrow(
                "SELECT * FROM users WHERE email = $1", data["sub"]["email"]
            )
            await conn.close()

            if not user:
                return Response(f"User not found", status_code=401)

        except jwt.ExpiredSignatureError:
            logging.error("ExpiredSignatureError")
            return Response("ExpiredSignatureError", status_code=401)
        except jwt.InvalidTokenError:
            logging.error("Invalid token")
            return Response("InvalidToken", status_code=401)
        except Exception as e:
            logging.error(e)
            return Response(f"Some exception {e}", status_code=401)
    elif key:
        try:
            conn = await asyncpg.connect(DATABASE_ADRESS)
            user = await conn.fetchrow("SELECT * FROM users WHERE api_key = $1", key)
            await conn.close()
            if not user:
                return Response(f"User not found", status_code=401)
            return Response("ok", status_code=200)
        except Exception as exp:
            logging.error(exp)
            return Response(f"{exp}", status_code=401)
    return Response("Invalid token and key", status_code=401)