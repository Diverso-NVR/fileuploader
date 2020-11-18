import os.path
import logging
import asyncio
import asyncpg
import jwt
import uvicorn
import uuid
from typing import List
from fastapi import APIRouter, UploadFile, File, status, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from aiofile import AIOFile
from google_functions import upload_to_google

SERVER_PATH = "bin_for_temp_vids/"

class DataForGoogle(BaseModel):
    file_name: str
    folder_name: str

router = APIRouter()

@router.get("/fileuploader/declare-upload")
async def declare_upload():
    """
    Says server to create file with random name and returns this name
    """

    file_name = str(uuid.uuid4().hex)

    logging.info(f"Was created {file_name}")

    # создаём пустой файл
    async with AIOFile(f"{SERVER_PATH}{file_name}.mp4", "wb") as f:
        pass
    return JSONResponse(status_code=status.HTTP_201_CREATED, content=file_name)


@router.put("/fileuploader/upload/{file_name}")
async def upload(
    file_name: str,
    file_in: bytes = File(...),
):
    """
    Gets file_name and download bytes to file with this name
    """

    if not os.path.isfile(f"{SERVER_PATH}{file_name}.mp4"):
        logging.error(f"File with name {file_name} was not found")
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND, content="file not found"
        )

    try:
        async with AIOFile(f"{SERVER_PATH}{file_name}.mp4", mode="ab") as file:
            await file.write(file_in)
            await file.fsync()
            logging.info(f"Writed in the {file_name}")
        return JSONResponse(status_code=status.HTTP_200_OK)

    except Exception as exp:
        logging.error(exp)
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.post("/fileuploader/declare-stop/{server_file_name}")
async def declare_stop(
    server_file_name: str,
    data_for_google: DataForGoogle,
):
    """
    Says code to start upload file to Google and delete it on our server
    """

    res_upld = await upload_to_google(
        data_for_google.file_name, data_for_google.folder_name, server_file_name
    )
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
