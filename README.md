# Fileuploader

## Использование этого модуля клиентом

Данный модуль включает в себя 2 рута:

Доки UI: https://nvr.miem.hse.ru/api/fileuploader/docs

- https://nvr.miem.hse.ru/api/fileuploader/files
  вы отправляете на данный адрес POST запорс с полями как в примере, вам возвращается id. По этому id загружаете дальше файлы вставляя его в url. Если ответ сервера 201, то всё хорошо

- https://nvr.miem.hse.ru/api/fileuploader/files/{file_id}
  вы отправляете на данный адрес PUT запросы с байтами или с файлами видео, согласно приведенному коду в конце README. Вместо file_id вы вставляете id, полученный по запросу в declare-upload. Возвращается код 200, если всё хорошо

## Пример кода для загрузки на сервер

### Common data

```python
api_key: str # nvr API key
file_path: str
file_name: str
folder_name: str # course code
file_size: int
room_name: str # 'Zoom' or 'MS Teams'
dt: str # iso format (%Y-%m-%dT%H:%M:%S): "2020-08-21T01:30:00"

api_url: str = 'https://nvr.miem.hse.ru/api/fileuploader'

headers = {"key": api_key}

file_size = os.stat(file_path).st_size
data = {
    "file_name": file_name,  # имя на диске гугла
    "folder_name": folder_name,
    "room_name": room_name,
    "file_size": file_size,  # размер файла
    "record_dt": dt,
}
```

### async

```python
import asyncio
import os

from aiohttp import ClientSession
from aiofile import AIOFile, Reader


async def go():
    async with ClientSession() as session:
        async with session.post(
            f"{api_url}/files", json=data, ssl=False, headers=headers
        ) as resp:
            resp__json = await resp.json()
            file_id = resp__json["file_id"]

        async with AIOFile(file_path, "rb") as afp:
            reader = Reader(afp, chunk_size=256 * 1024 * 20)  # загрузка по 5MB
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

### sync

```python
import requests


def main():
    res = requests.post(
        f"{api_url}/files", headers=headers, json=data
    )
    file_id = res.json()["file_id"]
    chunk_size = 256 * 1024 * 20 # 5 MB

    with open(file_path, "rb") as f:
        chunk = f.read(chunk_size) # 5 MB

        while len(chunk) > 0:
            resp = requests.put(
                f"{api_url}/files/{file_id}",
                headers=headers,
                files={"file_data": chunk},
            )
            print(resp.json())
            chunk = f.read(chunk_size)


if __name__ == "__main__":
    main()
```
