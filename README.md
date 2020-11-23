# Fileuploader

## Использование этого модуля клиентом

Данный модуль включает в себя 2 рута:

Доки UI: https://nvr.miem.hse.ru/api/fileuploader/docs

- https://nvr.miem.hse.ru/api/fileuploader/files/
  вы отправляете на данный адрес POST запорс с полями как в примере, вам возвращается id. По этому id загружаете дальше файлы вставляя его в url. Если ответ сервера 201, то всё хорошо

- https://nvr.miem.hse.ru/api/fileuploader/files/{file_id}
  вы отправляете на данный адрес PUT запросы с байтами или с файлами видео, согласно приведенному коду в конце README. Вместо file_id вы вставляете id, полученный по запросу в declare-upload. Возвращается код 200, если всё хорошо

### Пример кода для загрузки на сервер

```python
import asyncio
import os

from aiohttp import ClientSession
from aiofile import AIOFile, Reader


api_key: str # nvr API key
file_path: str
file_name: str
folder_name: str # course code
file_size: int
parent_id: str # "1weIs_vptfXVN20hSIpN9thL7Vh7VgH3h" for Zoom

api_url: str = 'https://nvr.miem.hse.ru/api/fileuploader'

headers = {"key": api_key}


async def go():
    file_size = str(os.stat(file_path).st_size)
    data = {
        "file_name": file_name,  # имя на диске гугла
        "folder_name": folder_name,  # имя папки для загрузки. Папка находится в parent_id директории
        "parent_folder_id": parent_id,  # сам parent_id
        "file_size": file_size,  # размер файла
    }

    async with ClientSession() as session:
        async with session.post(
            f"{api_url}/files/", json=data, ssl=False, headers=headers
        ) as resp:
            resp__json = await resp.json()
            file_id = resp__json["file_id"]

        async with AIOFile(file_path, "rb") as afp:
            reader = Reader(afp, chunk_size=256 * 1024 * 100)  # загрузка по 25MB
            async for chunk in reader:
                async with session.put(
                    f"{api_url}/files/{file_id}",
                    data={"file_data": chunk},
                    ssl=False,
                    headers=headers,
                ) as resp:
                    print(await resp.json())


asyncio.run(go())
```
