from datetime import datetime
import pickle
import os
import logging
from typing import List, Union, AsyncGenerator, Tuple

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

from aiohttp import ClientSession
import ujson

from .decorators import token_check
from .decorators import COROUTINE, GENERATOR
from .settings import settings
from .db import redis

logger = logging.getLogger("fileuploader")


class GoogleBase:
    __slots__ = (
        "_creds_path",
        "_token_path",
        "_scopes",
        "_creds",
        "_headers",
        "_httpsession",
    )

    def __init__(self, creds_path: str, token_path: str, scopes: Union[str, List[str]]):
        self._creds_path = creds_path
        self._token_path = token_path
        self._scopes = scopes
        self._creds = None

        try:
            self._httpsession = ClientSession(json_serialize=ujson.dumps)
        except RuntimeError:
            self._httpsession = None

        self._headers = {"Authorization": ""}

    def refresh_token(self) -> None:
        creds = None

        if os.path.exists(self._token_path):
            with open(self._token_path, "rb") as token:
                creds = pickle.load(token)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self._creds_path, self._scopes
                )
                creds = flow.run_local_server(port=0)

            with open(self._token_path, "wb") as token:
                pickle.dump(creds, token)

        self._creds = creds
        self._headers["Authorization"] = f"Bearer {creds.token}"


class GCalendar(GoogleBase):
    API_URL = "https://www.googleapis.com/calendar/v3"

    @token_check(COROUTINE)
    async def add_attachments(
        self, calendar_id: str, event_id: str, file_id: str, event_name: str
    ) -> str:
        logger.info(
            f"Adding attachments to calendar with id {calendar_id}, event with id {event_id},"
            f"event name is {event_name}"
        )

        resp = await self._httpsession.get(
            f"{self.API_URL}/calendars/{calendar_id}/events/{event_id}",
            headers=self._headers,
            ssl=False,
        )
        async with resp:
            event = await resp.json()

        changes = {
            "attachments": [
                {
                    "fileUrl": f"https://drive.google.com/a/auditory.ru/file/d/{file_id}/view?usp=drive_web",
                    "title": event_name,
                    "fileId": file_id,
                    "mimeType": "video/mp4",
                    "iconLink": "https://drive-thirdparty.googleusercontent.com/16/type/video/mp4",
                }
            ]
        }

        resp = await self._httpsession.patch(
            f"{self.API_URL}/calendars/{calendar_id}/events/{event_id}",
            headers=self._headers,
            ssl=False,
            json=changes,
            params={"supportsAttachments": "true"},
        )
        async with resp:
            pass

        logger.info(
            f"Added attachments to calendar with id {calendar_id}, event with id {event_id}"
        )

        return event.get("description", "")


class GDrive(GoogleBase):
    API_URL = "https://www.googleapis.com/drive/v3"
    UPLOAD_API_URL = "https://www.googleapis.com/upload/drive/v3"

    @token_check(COROUTINE)
    async def declare_upload_to_google(self, file_id: str):
        file = await redis.load_data(file_id)
        logger.info(f"declare_upload_to_google got {file} for {file_id} from redis")

        root_folder_id = file["room_drive_id"]
        file_name = file["file_name"]

        record_dt = file["record_dt"]
        record_dt = datetime.strptime(record_dt, "%Y-%m-%dT%H:%M:%S")

        date_folder_id = await self.find_folder(str(record_dt.date()), root_folder_id)

        meta_data = {"name": file_name, "parents": [date_folder_id]}
        async with self._httpsession.post(
            f"{self.UPLOAD_API_URL}/files?uploadType=resumable",
            headers={**self._headers, **{"X-Upload-Content-Type": "video/mp4"}},
            json=meta_data,
            ssl=False,
        ) as resp:
            file["session_url"] = resp.headers.get("Location")

        await redis.dump_data(file_id, file)

        logger.info(f"Declared upload {file_id} to google with data: {file}")

    async def find_folder(self, date: str, root_folder_id: str) -> str:
        async for folder_id, folder_parent_ids in self.get_folders_by_name(date):
            if root_folder_id in folder_parent_ids:
                break
        else:
            folder_id = await self.create_folder(date, root_folder_id)

        return folder_id

    @token_check(COROUTINE)
    async def upload_to_google(self, file_id: str, file_data: bytes) -> str:
        """
        Uploads file to google and if needed use create_folder()
        """
        file = await redis.load_data(file_id)
        logger.info(f"upload_to_google got {file} for {file_id} from redis")

        file_size = file["file_size"]
        session_url = file["session_url"]
        received_bytes_lower = file["received_bytes_lower"]

        chunk_size = len(file_data)
        chunk_range = (
            f"bytes {received_bytes_lower}-{received_bytes_lower + chunk_size - 1}"
        )
        logger.info(f"Uploading {chunk_range} for {file_id}")

        async with self._httpsession.put(
            session_url,
            data=file_data,
            ssl=False,
            headers={
                "Content-Length": str(chunk_size),
                "Content-Range": f"{chunk_range}/{file_size}",
            },
        ) as resp:
            chunk_range = resp.headers.get("Range")

            try:
                resp_json = await resp.json()
                file["drive_file_id"] = resp_json["id"]
            except Exception:
                pass

            if chunk_range is None:
                resp_json = await resp.json()

                await redis.remove_data(file_id)
                logger.info(f"Uploaded {file_id} to google")

                return resp_json["id"]

            _, bytes_data = chunk_range.split("=")
            _, received_bytes_lower = bytes_data.split("-")
            received_bytes_lower = int(received_bytes_lower) + 1
            file["received_bytes_lower"] = received_bytes_lower

        await redis.dump_data(file_id, file)

        logger.info(f"Continuing uploading {file_id} to google with data: {file}")

    @token_check(COROUTINE)
    async def create_folder(self, folder_name: str, folder_parent_id: str) -> str:
        """
        Creates folder in format: 'folder_name'
        """
        logger.info(
            f"Creating folder with name {folder_name} inside folder with id {folder_parent_id}"
        )

        meta_data = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder",
        }
        if folder_parent_id:
            meta_data["parents"] = [folder_parent_id]

        async with self._httpsession.post(
            f"{self.API_URL}/files", headers=self._headers, json=meta_data, ssl=False
        ) as resp:
            resp_json = await resp.json()
            logger.info(f"create_folder response: {resp_json}")
            folder_id = resp_json["id"]

        new_perm = {"type": "anyone", "role": "reader"}

        resp = await self._httpsession.post(
            f"{self.API_URL}/files/{folder_id}/permissions",
            headers=self._headers,
            json=new_perm,
            ssl=False,
        )
        resp.close()

        return folder_id

    @token_check(GENERATOR)
    async def get_folders_by_name(
        self,
        name: str,
    ) -> AsyncGenerator[Tuple[str, List[str]], None]:
        logger.info(f"Getting the id of folder with name {name}")

        params = dict(
            fields="nextPageToken, files(name, id, parents)",
            q=f"mimeType='application/vnd.google-apps.folder'and name='{name}'",
            spaces="drive",
        )
        folders = []
        page_token = ""

        while page_token is not False:
            async with self._httpsession.get(
                f"{self.API_URL}/files?pageToken={page_token}",
                headers=self._headers,
                params=params,
                ssl=False,
            ) as resp:
                resp_json = await resp.json()
                logger.info(f"get_folders_by_name response: {resp_json}")
                page_token = resp_json.get("nextPageToken", False)

                folders = resp_json.get("files", [])
                for folder in folders:
                    yield folder["id"], folder.get("parents", [])


calendar_service = GCalendar(
    creds_path=settings.google_creds_path,
    token_path=settings.google_calendar_token_path,
    scopes=settings.google_calendar_scopes,
)
drive_service = GDrive(
    creds_path=settings.google_creds_path,
    token_path=settings.google_drive_token_path,
    scopes=settings.google_drive_scopes,
)
