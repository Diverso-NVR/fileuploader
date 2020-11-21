import os
import logging
from sys import getdefaultencoding
from aiohttp import ClientSession
from aiofile import AIOFile, Reader
from main import r, creds
from google.auth.transport.requests import Request
import json


API_URL = "https://www.googleapis.com/drive/v3"


TOKEN_PATH = "creds/tokenDrive.pickle"
CREDS_PATH = "creds/credentials.json"
SCOPES = "https://www.googleapis.com/auth/drive"
UPLOAD_API_URL = "https://www.googleapis.com/upload/drive/v3"

PARENT_ID = "1weIs_vptfXVN20hSIpN9thL7Vh7VgH3h"

SERVER_PATH = os.environ.get("SERVER_PATH")

HEADERS = None


def possible_update_creds(function_to_decorate):
    async def wrapper(*args, **kwards):
        if creds.expired:
            creds.refresh(Request())
        global HEADERS
        HEADERS = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {creds.token}",
        }
        return await function_to_decorate(*args, **kwards)

    return wrapper


@possible_update_creds
async def declare_upload_to_google(file_id: str):
    dict = r.hgetall(file_id)

    folder_name = dict[b"folder_name"].decode("utf-8")
    parent_folder_id = dict[b"parent_folder_id"].decode("utf-8")
    file_name = dict[b"file_name"].decode("utf-8")

    folder_id = await get_folder_by_name(folder_name)

    if not folder_id:
        folder_id = await create_folder(folder_name, parent_folder_id)
        pass
    else:
        folder_id = list(folder_id.keys())[0]
        r.hset(file_id, "folder_id", folder_id)

    meta_data = {"name": file_name, "parents": [folder_id]}
    try:
        async with ClientSession() as session:
            async with session.post(
                f"{UPLOAD_API_URL}/files?uploadType=resumable",
                headers={**HEADERS, **{"X-Upload-Content-Type": "video/mp4"}},
                json=meta_data,
                ssl=False,
            ) as resp:
                session_url = resp.headers.get("Location")
                r.hset(file_id, "session_url", session_url)
        return True
    except Exception as exp:
        logging.error(exp)
        return False


@possible_update_creds
async def upload_to_google(file_id: str, file_in: bytes) -> str:
    """
    Uploads file to google and if needed use create_folder()
    """
    dict = r.hgetall(file_id)

    file_size = dict[b"file_size"]
    session_url = dict[b"session_url"].decode("utf-8")

    if r.hget(file_id, "received_bytes_lower") == b"None":
        r.hset(file_id, "received_bytes_lower", 0)
        received_bytes_lower = b"0"
    else:
        received_bytes_lower = r.hget(file_id, "received_bytes_lower")

    received_bytes_lower = int(received_bytes_lower.decode("utf-8"))

    chunk_size = len(file_in)
    chunk_range = (
        f"bytes {received_bytes_lower}-{received_bytes_lower + chunk_size - 1}"
    )
    try:
        async with ClientSession() as session:
            async with session.put(
                session_url,
                data=file_in,
                ssl=False,
                headers={
                    "Content-Length": str(chunk_size),
                    "Content-Range": f"{chunk_range}/{file_size}",
                },
            ) as resp:
                print(await resp.text())
                chunk_range = resp.headers.get("Range")
                if chunk_range is None:
                    r.delete(file_id)
                    return True

                _, bytes_data = chunk_range.split("=")
                _, received_bytes_lower = bytes_data.split("-")
                received_bytes_lower = int(received_bytes_lower) + 1
                r.hset(file_id, "received_bytes_lower", received_bytes_lower)
                logging.info(f"Uploaded {file_id}")
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
        while page_token is not False:
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
