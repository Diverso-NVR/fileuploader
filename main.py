import uvicorn
from typing import List
from fastapi import FastAPI, Depends, UploadFile, File, status, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uuid 
from aiofile import AIOFile
import os.path
import logging
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
from aiohttp import ClientSession
from aiofile import AIOFile, Reader
# from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import asyncio
import asyncpg
import jwt




TOKEN_PATH = "creds/tokenDrive.pickle"
CREDS_PATH = "creds/credentials.json"
SCOPES = 'https://www.googleapis.com/auth/drive'
API_URL = 'https://www.googleapis.com/drive/v3'
UPLOAD_API_URL = 'https://www.googleapis.com/upload/drive/v3'
PARENT_ID = '1weIs_vptfXVN20hSIpN9thL7Vh7VgH3h'
# SERVER_PATH = '/root/temp_vids'
SERVER_PATH = 'bin_for_temp_vids/'
DATABASE_ADRESS = os.environ.get('DB_URL')
SECRET_KEY = '123'
tok = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.19zZfcq5d40KCY6Poj4t7OFB_UM-eDv00bIcX5TY9fs'

class DataForGoogle(BaseModel):
    file_name: str
    folder_name: str
    #сюда можно добавить поле для того, чтобы выбрать какую папку считать родительской


logging.basicConfig(filename='logging/logs.log', filemode='a',
   format='%(asctime)s - %(message)s', level=logging.INFO)


app = FastAPI()

creds = None

def creds_generate():
    global creds
    # if you do not have creds
    # flow = InstalledAppFlow.from_client_secrets_file(
    #             CREDS_PATH, SCOPES)
    # creds = flow.run_local_server(port=0)
    # with open(TOKEN_PATH, 'wb') as token:
    #     pickle.dump(creds, token)
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, 'wb') as token:
            pickle.dump(creds, token)


creds_generate()

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {creds.token}"
}

@app.get('/fileuploader/declare-upload')
async def declare_upload(Authentification: str = Header(...),  key: str = Header(...),):
    """
    Says server to create file with random name and returns this name
    """
    token = get_token_auth_header(Authentification)
    await check_jwt_token_and_key(token, key)

    file_name = str(uuid.uuid4().hex)

    logging.info(f'Was created {file_name}')

    #создаём пустой файл
    async with AIOFile(f'{SERVER_PATH}{file_name}.mp4', 'wb') as f:
        pass
    return JSONResponse(status_code=status.HTTP_201_CREATED, content=file_name)


@app.put("/fileuploader/upload/{file_name}")
async def upload(file_name: str, Authentification: str = Header(...),
    key: str = Header(...), file_in: bytes = File(...)):
    """
    Gets file_name and download bytes to file with this name
    """
    token = get_token_auth_header(Authentification)
    check_jwt_token_and_key(token, key)

    if not os.path.isfile(f'{SERVER_PATH}{file_name}.mp4'):
        logging.error(f'File with name {file_name} was not found')
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content='file not found')

    try:
        async with AIOFile(f'{SERVER_PATH}{file_name}.mp4', mode='ab') as file:
            await file.write(file_in)
            await file.fsync()
            logging.info(f'Writed in the {file_name}')
        return JSONResponse(status_code=status.HTTP_200_OK)

    except Exception as exp:
        logging.error(exp)
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.post("/fileuploader/declare-stop/{server_file_name}")
async def declare_stop(server_file_name: str, data_for_google: DataForGoogle,
 Authentification: str = Header(...), key: str = Header(...)):
    """
    Says code to start upload file to Google and delete it on our server
    """
    token = get_token_auth_header(Authentification)
    check_jwt_token_and_key(token, key)

    res_upld = await upload_to_google(data_for_google.file_name, 
        data_for_google.folder_name, server_file_name)
    if res_upld:
        try:    
            os.remove(f'{SERVER_PATH}{server_file_name}.mp4')
            logging.info(f'Deleted file: {server_file_name}')
            return JSONResponse(status_code=status.HTTP_200_OK)
        except Exception as exp:
            logging.info(f'Error while deleting {server_file_name} err: {exp}')
            return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        logging.error(f'something bad happend, file {server_file_name} was not uploaded and not deleted')
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    
async def upload_to_google(google_file_name: str, folder_name: str, server_file_name: str) -> str:
    """
    Uploads file to google and if needed use create_folder()
    """
    folder_id = await get_folder_by_name(folder_name)

    if not folder_id:
        folder_id = await create_folder(folder_name)
    else:
        folder_id = list(folder_id.keys())[0]

    full_server_path = f'{SERVER_PATH}{server_file_name}.mp4'
    
    meta_data = {
        "name": google_file_name,
        "parents": [folder_id]
    }
    try:
        async with ClientSession() as session:
            async with session.post(f'{UPLOAD_API_URL}/files?uploadType=resumable',
                                    headers={**HEADERS,
                                            **{"X-Upload-Content-Type": "video/mp4"}},
                                    json=meta_data,
                                    ssl=False) as resp:
                session_url = resp.headers.get('Location')
            
            async with AIOFile(full_server_path, 'rb') as afp:
                file_size = str(os.stat(full_server_path).st_size)
                reader = Reader(afp, chunk_size=256 * 1024 * 100)  # 25MB
                received_bytes_lower = 0
                async for chunk in reader:
                    chunk_size = len(chunk)
                    chunk_range = f"bytes {received_bytes_lower}-{received_bytes_lower + chunk_size - 1}"

                    async with session.put(session_url, data=chunk, ssl=False,
                                        headers={"Content-Length": str(chunk_size),
                                                    "Content-Range": f"{chunk_range}/{file_size}"}) as resp:
                        chunk_range = resp.headers.get('Range')
                        if chunk_range is None:
                            break

                        _, bytes_data = chunk_range.split('=')
                        _, received_bytes_lower = bytes_data.split('-')
                        received_bytes_lower = int(received_bytes_lower) + 1

        logging.info(f'Uploaded {full_server_path}')
        return True
    except Exception as exp:
        logging.error(exp)
        return False

async def create_folder(folder_name: str, folder_parent_id: str = PARENT_ID) -> str:
    """
    Creates folder in format: 'folder_name'
    """
    logging.info(
        f'Creating folder with name {folder_name} inside folder with id {folder_parent_id}')

    meta_data = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder'
    }
    if folder_parent_id:
        meta_data['parents'] = [folder_parent_id]

    async with ClientSession() as session:
        async with session.post(f'{API_URL}/files',
                                headers=HEADERS,
                                json=meta_data,
                                ssl=False) as resp:

            resp_json = await resp.json()
            folder_id = resp_json['id']

        new_perm = {
            'type': 'anyone',
            'role': 'reader'
        }

        async with session.post(f'{API_URL}/files/{folder_id}/permissions',
                                headers=HEADERS,
                                json=new_perm,
                                ssl=False) as resp:
            pass

    return folder_id


async def get_folder_by_name(name: str) -> dict:
    logging.info(f'Getting the id of folder with name {name}')

    params = dict(
        fields='nextPageToken, files(name, id, parents)',
        q=f"mimeType='application/vnd.google-apps.folder'and name='{name}'",
        spaces='drive'
    )
    folders = []
    page_token = ''

    async with ClientSession() as session:
        while page_token != False:
            async with session.get(f'{API_URL}/files?pageToken={page_token}',
                                   headers=HEADERS, params=params,
                                   ssl=False) as resp:
                resp_json = await resp.json()
                folders.extend(resp_json.get('files', []))
                page_token = resp_json.get('nextPageToken', False)

    return {folder['id']: folder.get('parents', []) for folder in folders}

def get_token_auth_header(authorization):
    parts = authorization.split()

    if parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=401, 
            detail='Authorization header must start with Bearer')
    elif len(parts) == 1:
        raise HTTPException(
            status_code=401, 
            detail='Authorization token not found')
    elif len(parts) > 2:
        raise HTTPException(
            status_code=401, 
            detail='Authorization header be Bearer token')
    token = parts[1]
    return token

async def check_jwt_token_and_key(token: str, key: str):
    #как получить secret key?
    if token:
        try:
            data = jwt.decode(token, SECRET_KEY)
            conn = await asyncpg.connect(DATABASE_ADRESS)
            user = await conn.fetchrow(
                'SELECT * FROM users WHERE email = $1', data['sub']['email']
            )
            await conn.close()

            if not user:
                raise HTTPException(
                    status_code=401, 
                    detail='User with this token not found')
            return True

        except jwt.ExpiredSignatureError:
            logging.error('ExpiredSignatureError')
            raise HTTPException(
                    status_code=401, 
                    detail='TokenExpired')
        except jwt.InvalidTokenError:
            logging.error('Invalid token')
            raise HTTPException(
                    status_code=401, 
                    detail='Invalid token')
        except Exception as e:
            logging.error(e)
            raise HTTPException(
                    status_code=401, 
                    detail=e)
    elif key:
        try:
            conn = await asyncpg.connect(DATABASE_ADRESS)
            user = await conn.fetchrow(
                'SELECT * FROM users WHERE api_key = $1', key
            )
            await conn.close()
            if not user:
                raise HTTPException(
                    status_code=401, 
                    detail='wrong api key')
            return True
        except Exception as exp:
            logging.error(exp)
            raise HTTPException(
                    status_code=500, 
                    detail='Server error')
    raise HTTPException(
                    status_code=401, 
                    detail='Invalid token and key')






if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5005)
#Is essential to wrap 'with' using try 
#logging возможно в отдельный файл переписать
#можно ли в логгировании просто exception писать или как-то по-другому нормально выводить ошибку, чтобы было понятно че как
#асинхронное удаление хз как сделать

#для прода
# os.environ['DB_URL'] -- задать
# добавить слеши  в именах в папках
# заменить получение секретного ключа