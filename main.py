import uvicorn
from typing import List
from fastapi import FastAPI, Depends, UploadFile, File, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uuid 
from aiofile import AIOFile
import os.path
import logging


logging.basicConfig(filename='logging/logs.log', filemode='a',
    format='%(asctime)s - %(message)s', level=logging.INFO)
app = FastAPI()

x = uuid.uuid4()


@app.post('/declare-upload')
async def declare_upload():
    """Says server to create file with random name and returns this name"""
    file_name = str(uuid.uuid4())

    #проверка, что файла с таким именем нет
    while os.path.isfile(f'bin_for_temp_vids/{file_name}.mp4'): 
        file_name = str(uuid.uuid4())
    
    logging.info(f'Was created {file_name}')

    #создаём пустой файл
    async with AIOFile(f'bin_for_temp_vids/{file_name}.mp4', 'wb') as f:
        pass
    return JSONResponse(status_code=status.HTTP_201_CREATED, content=file_name)


@app.put("/upload/{file_name}")
async def upload(file_name: str, file_in: bytes = File(...)):
    """Gets file_name and download bytes to file with this name"""
    if not os.path.isfile(f'bin_for_temp_vids/{file_name}.mp4'):
        logging.error(f'File with name {file_name} was not found')
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content='file not found')

    try:
        async with AIOFile(f'bin_for_temp_vids/{file_name}.mp4', mode='ab') as file:
            await file.write(file_in)
            await file.fsync()
            logging.info(f'Writing in the {file_name}')
            #чек ошибку
        return JSONResponse(status_code=status.HTTP_200_OK)
    except Exception as exp:
        logging.error(exp)
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.post("/declare-stop/{file_name}")
async def declare_stop(file_name: str):
    """Says to code to start upload file to Google and delete it on server"""
    try:
        os.remove(f'bin_for_temp_vids/{file_name}.mp4')
        logging.info(f'Deleted file: {file_name}')
        return JSONResponse(status_code=status.HTTP_200_OK)
    except Exception as exp:
        logging.info(f'Error while deleting {file_name} err: {exp}')
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    #удалить файл и начать закачку его на сервер
    

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

#TODO safe generation of uuid, ask kuderr
#Is essential to wrap 'with' using try 
#logging возможно в отдельный файл переписать
#можно ли в логгировании просто exception писать или как-то по-другому нормально выводить ошибку, чтобы было понятно че как
#асинхронное удаление хз как сделать