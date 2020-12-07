import logging
import uuid

from fastapi import APIRouter, File
from pydantic import BaseModel
from pydantic.fields import Field

from .google import drive_service
from .db import redis, psql

logger = logging.getLogger("fileuploader")


class OnlineRecord(BaseModel):
    file_name: str = Field(
        ...,
        example="Физика БИВ171",
        description="File name under which file will be saved on drive",
    )
    folder_name: str = Field(
        ...,
        example="БИВ171",
        description="Folder name in parent folder, where records will be stored by date",
    )
    room_name: str = Field(
        ..., example="Zoom", description="'Zoom' or 'MS Teams' for now"
    )
    file_size: int = Field(..., gt=0, example=1024, description="File size in bytes")
    record_dt: str = Field(
        ...,
        example="2020-08-21T01:30:00",
        description="Moscow time. Will be parsed to create date folder for records in 'folder_name' folder",
    )


router = APIRouter()


@router.post("/files", status_code=201)
async def declare_upload(record: OnlineRecord):
    """
    Says server to create file with random id and returns this id
    """

    file_id = str(uuid.uuid4().hex)
    room = await psql.get_room(record.room_name)

    await redis.dump_data(
        file_id,
        {
            "file_name": record.file_name,
            "folder_name": record.folder_name,
            "file_size": record.file_size,
            "record_dt": record.record_dt,
            "room_drive_id": room.get("drive").split("/")[0],
            "received_bytes_lower": 0,
            "session_url": None,
        },
    )

    await drive_service.declare_upload_to_google(file_id)
    logger.info(f"Was created {file_id}")

    return {"file_id": file_id}


@router.put("/files/{file_id}")
async def upload(
    file_id: str,
    file_data: bytes = File(...),
):
    """
    Gets file_name and download bytes to drive with its name
    """
    logger.info(f"Recieved {len(file_data)} bytes")
    await drive_service.upload_to_google(file_id, file_data)
    return {"message": f"Uploaded {len(file_data)} for {file_id}"}
