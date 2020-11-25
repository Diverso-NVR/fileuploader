import logging
import uuid

from fastapi import APIRouter, File, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import ujson

from .google_functions import upload_to_google, declare_upload_to_google
from .settings import settings
from .connections import redis

logger = logging.getLogger("fileuploader")

VIDS_PATH = settings.vids_path


class DataForGoogle(BaseModel):
    file_name: str
    folder_name: str
    parent_folder_id: str
    file_size: str


router = APIRouter()


@router.post("/files/", status_code=201)
async def declare_upload(data_for_google: DataForGoogle):
    """
    Says server to create file with random name and returns this name
    """

    file_id = str(uuid.uuid4().hex)
    await redis.set(
        file_id,
        ujson.dumps(
            {
                "file_name": data_for_google.file_name,
                "folder_name": data_for_google.folder_name,
                "parent_folder_id": data_for_google.parent_folder_id,
                "file_size": data_for_google.file_size,
                "received_bytes_lower": 0,
                "session_url": None,
            }
        ),
    )

    await declare_upload_to_google(file_id)
    logger.info(f"Was created {file_id}")

    return {"file_id": file_id}


@router.put("/files/{file_id}")
async def upload(
    file_id: str,
    file_data: bytes = File(...),
):
    """
    Gets file_name and download bytes to file with this name
    """
    logger.info(f"Recieved {len(file_data)} bytes")
    await upload_to_google(file_id, file_data)
    return {"message": f"Uploaded {len(file_data)} for {file_id}"}
