import os.path
import logging
import uuid
import pickle
from fastapi import APIRouter, File, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from aiofile import AIOFile
from google_functions import upload_to_google, declare_upload_to_google
from main import r


SERVER_PATH = os.environ.get("SERVER_PATH")


class DataForGoogle(BaseModel):
    file_name: str
    folder_name: str
    parent_folder_id: str
    file_size: str


router = APIRouter()

# key -- server_file_name //id
# folder_id
# file_size
# recieved bytes lower сначала 0
#


@router.post("/declare-upload/")
async def declare_upload(data_for_google: DataForGoogle):
    """
    Says server to create file with random name and returns this name
    """
    r.mset({"Croatia": "Zagreb", "Bahamas": "Nassau"})

    file_id = str(uuid.uuid4().hex)

    r.hmset(
        f"{file_id}",
        {
            "file_name": data_for_google.file_name,
            "folder_name": data_for_google.folder_name,
            "parent_folder_id": data_for_google.parent_folder_id,
            "file_size": data_for_google.file_size,
            "received_bytes_lower": "None",
            "session_url": "None",
        },
    )
    if await declare_upload_to_google(file_id):
        logging.info(f"Was created {file_id}")

        return JSONResponse(status_code=status.HTTP_201_CREATED, content=file_id)
    else:
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.put("/upload/{file_id}")
async def upload(
    file_id: str,
    file_in: bytes = File(...),
):
    """
    Gets file_name and download bytes to file with this name
    """
    dict = r.hgetall(file_id)

    res_upld = await upload_to_google(file_id, file_in)
    if res_upld:
        return JSONResponse(status_code=status.HTTP_201_CREATED, content="Загружено")
    else:
        return JSONResponse(
            status_code=status.HTTP_201_CREATED, content="Ошибка на сервере"
        )


@router.post("/declare-stop/{server_file_name}")
async def declare_stop(
    server_file_name: str,
):
    """
    Says code to start upload file to Google and delete it on our server
    """

    if res_upld:
        try:
            os.remove(f"{SERVER_PATH}{server_file_name}.mp4")
            logging.info(f"Deleted file: {server_file_name}")
            return JSONResponse(status_code=status.HTTP_200_OK)
        except Exception as exp:
            logging.info(f"Error while deleting {server_file_name} err: {exp}")
            return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        logging.error(
            f"something bad happend, file {server_file_name} was not uploaded and not deleted"
        )
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
