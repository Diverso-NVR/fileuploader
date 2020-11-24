import os
import logging
import pickle

from aiohttp import ClientSession
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
import ujson

from .settings import settings
from .connections import redis

logger = logging.getLogger("fileuploader")

SCOPES = "https://www.googleapis.com/auth/drive"
API_URL = "https://www.googleapis.com/drive/v3"
UPLOAD_API_URL = "https://www.googleapis.com/upload/drive/v3"

CREDS_PATH = settings.google_creds_path
TOKEN_PATH = settings.google_token_path

headers = {}
creds = None


def creds_generate():
    global creds
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


creds_generate()


def token_check(func):
    async def wrapper(*args, **kwargs):
        if creds.expired:
            logger.info("Recreating google token")
            creds_generate()

        headers["Authorization"] = f"Bearer {creds.token}"
        return await func(*args, **kwargs)

    return wrapper


@token_check
async def declare_upload_to_google(file_id: str):
    file = await redis.get(file_id, encoding="utf-8")
    logger.info(f"declare_upload_to_google got {file} for {file_id} from redis")
    file = ujson.loads(file)

    folder_name = file["folder_name"]
    parent_folder_id = file["parent_folder_id"]
    file_name = file["file_name"]

    folders = await get_folder_by_name(folder_name)
    for folder_id, folder_parent_ids in folders.items():
        if parent_folder_id in folder_parent_ids:
            break
    else:
        folder_id = await create_folder(folder_name, parent_folder_id)

    file["folder_id"] = folder_id

    meta_data = {"name": file_name, "parents": [folder_id]}
    async with ClientSession() as session:
        async with session.post(
            f"{UPLOAD_API_URL}/files?uploadType=resumable",
            headers={**headers, **{"X-Upload-Content-Type": "video/mp4"}},
            json=meta_data,
            ssl=False,
        ) as resp:
            file["session_url"] = resp.headers.get("Location")

    await redis.set(
        file_id,
        ujson.dumps(file),
    )

    logger.info(f"Declared upload {file_id} to google with data: {file}")


@token_check
async def upload_to_google(file_id: str, file_data: bytes) -> str:
    """
    Uploads file to google and if needed use create_folder()
    """
    file = await redis.get(file_id, encoding="utf-8")
    logger.info(f"upload_to_google got {file} for {file_id} from redis")
    file = ujson.loads(file)

    file_size = file["file_size"]
    session_url = file["session_url"]
    received_bytes_lower = file["received_bytes_lower"]

    chunk_size = len(file_data)
    chunk_range = (
        f"bytes {received_bytes_lower}-{received_bytes_lower + chunk_size - 1}"
    )
    logger.info(f"Uploading {chunk_range} for {file_id}")

    async with ClientSession() as session:
        async with session.put(
            session_url,
            data=file_data,
            ssl=False,
            headers={
                "Content-Length": str(chunk_size),
                "Content-Range": f"{chunk_range}/{file_size}",
            },
        ) as resp:
            chunk_range = resp.headers.get("Range")
            if chunk_range is None:
                await redis.delete(file_id)
                logger.info(f"Uploaded {file_id} to google")
                return

            _, bytes_data = chunk_range.split("=")
            _, received_bytes_lower = bytes_data.split("-")
            received_bytes_lower = int(received_bytes_lower) + 1
            file["received_bytes_lower"] = received_bytes_lower

    await redis.set(
        file_id,
        ujson.dumps(file),
    )
    logger.info(f"Continuing uploading {file_id} to google with data: {file}")


@token_check
async def create_folder(folder_name: str, folder_parent_id: str) -> str:
    """
    Creates folder in format: 'folder_name'
    """
    logger.info(
        f"Creating folder with name {folder_name} inside folder with id {folder_parent_id}"
    )

    meta_data = {"name": folder_name, "mimeType": "application/vnd.google-apps.folder"}
    if folder_parent_id:
        meta_data["parents"] = [folder_parent_id]

    async with ClientSession() as session:
        async with session.post(
            f"{API_URL}/files", headers=headers, json=meta_data, ssl=False
        ) as resp:
            resp_json = await resp.json()
            logger.info(f"create_folder response: {resp_json}")
            folder_id = resp_json["id"]

        new_perm = {"type": "anyone", "role": "reader"}

        resp = await session.post(
            f"{API_URL}/files/{folder_id}/permissions",
            headers=headers,
            json=new_perm,
            ssl=False,
        )
        resp.close()

    return folder_id


@token_check
async def get_folder_by_name(name: str) -> dict:
    logger.info(f"Getting the id of folder with name {name}")

    params = dict(
        fields="nextPageToken, files(name, id, parents)",
        q=f"mimeType='application/vnd.google-apps.folder'and name='{name}'",
        spaces="drive",
    )
    folders = []
    page_token = ""

    async with ClientSession() as session:
        while page_token is not False:
            async with session.get(
                f"{API_URL}/files?pageToken={page_token}",
                headers=headers,
                params=params,
                ssl=False,
            ) as resp:
                resp_json = await resp.json()
                logger.info(f"get_folder_by_name response: {resp_json}")
                folders.extend(resp_json.get("files", []))
                page_token = resp_json.get("nextPageToken", False)

    return {folder["id"]: folder.get("parents", []) for folder in folders}
