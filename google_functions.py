import os
import pickle
import logging
from aiohttp import ClientSession
from aiofile import AIOFile, Reader
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request


API_URL = "https://www.googleapis.com/drive/v3"

TOKEN_PATH = "creds/tokenDrive.pickle"
CREDS_PATH = "creds/credentials.json"
SCOPES = "https://www.googleapis.com/auth/drive"
UPLOAD_API_URL = "https://www.googleapis.com/upload/drive/v3"
PARENT_ID = "1weIs_vptfXVN20hSIpN9thL7Vh7VgH3h"
# SERVER_PATH = '/root/temp_vids'

def possible_update_creds(function_to_decorate):
    # Внутри себя декоратор определяет функцию-"обёртку". Она будет обёрнута вокруг декорируемой,
    # получая возможность исполнять произвольный код до и после неё.
    def wrapper():
        if creds.expired:
            creds.refresh(Request())
            HEADERS = {"Content-Type": "application/json", "Authorization": f"Bearer {creds.token}"}
        function_to_decorate()
    return wrapper

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
        with open(TOKEN_PATH, "rb") as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, "wb") as token:
            pickle.dump(creds, token)





@possible_update_creds
async def upload_to_google(
    google_file_name: str,
    folder_name: str, 
    server_file_name: str
) -> str:
    """
    Uploads file to google and if needed use create_folder()
    """
    folder_id = await get_folder_by_name(folder_name)

    if not folder_id:
        folder_id = await create_folder(folder_name)
    else:
        folder_id = list(folder_id.keys())[0]

    full_server_path = f"{SERVER_PATH}{server_file_name}.mp4"

    meta_data = {"name": google_file_name, "parents": [folder_id]}
    try:
        async with ClientSession() as session:
            async with session.post(
                f"{UPLOAD_API_URL}/files?uploadType=resumable",
                headers={**HEADERS, **{"X-Upload-Content-Type": "video/mp4"}},
                json=meta_data,
                ssl=False,
            ) as resp:
                session_url = resp.headers.get("Location")

            async with AIOFile(full_server_path, "rb") as afp:
                file_size = str(os.stat(full_server_path).st_size)
                reader = Reader(afp, chunk_size=256 * 1024 * 100)  # 25MB
                received_bytes_lower = 0
                async for chunk in reader:
                    chunk_size = len(chunk)
                    chunk_range = f"bytes {received_bytes_lower}-{received_bytes_lower + chunk_size - 1}"

                    async with session.put(
                        session_url,
                        data=chunk,
                        ssl=False,
                        headers={
                            "Content-Length": str(chunk_size),
                            "Content-Range": f"{chunk_range}/{file_size}",
                        },
                    ) as resp:
                        chunk_range = resp.headers.get("Range")
                        if chunk_range is None:
                            break

                        _, bytes_data = chunk_range.split("=")
                        _, received_bytes_lower = bytes_data.split("-")
                        received_bytes_lower = int(received_bytes_lower) + 1

        logging.info(f"Uploaded {full_server_path}")
        return True
    except Exception as exp:
        logging.error(exp)
        return False

@possible_update_creds
async def create_folder(folder_name: str, folder_parent_id: str = PARENT_ID) -> str:
    """
    Creates folder in format: 'folder_name'
    """
    logging.info(
        f"Creating folder with name {folder_name} inside folder with id {folder_parent_id}"
    )

    meta_data = {"name": folder_name, "mimeType": "application/vnd.google-apps.folder"}
    if folder_parent_id:
        meta_data["parents"] = [folder_parent_id]

    async with ClientSession() as session:
        async with session.post(
            f"{API_URL}/files", headers=HEADERS, json=meta_data, ssl=False
        ) as resp:

            resp_json = await resp.json()
            folder_id = resp_json["id"]

        new_perm = {"type": "anyone", "role": "reader"}

        async with session.post(
            f"{API_URL}/files/{folder_id}/permissions",
            headers=HEADERS,
            json=new_perm,
            ssl=False,
        ) as resp:
            pass

    return folder_id

@possible_update_creds
async def get_folder_by_name(name: str) -> dict:
    logging.info(f"Getting the id of folder with name {name}")

    params = dict(
        fields="nextPageToken, files(name, id, parents)",
        q=f"mimeType='application/vnd.google-apps.folder'and name='{name}'",
        spaces="drive",
    )
    folders = []
    page_token = ""

    async with ClientSession() as session:
        while page_token != False:
            async with session.get(
                f"{API_URL}/files?pageToken={page_token}",
                headers=HEADERS,
                params=params,
                ssl=False,
            ) as resp:
                resp_json = await resp.json()
                folders.extend(resp_json.get("files", []))
                page_token = resp_json.get("nextPageToken", False)

    return {folder["id"]: folder.get("parents", []) for folder in folders}


