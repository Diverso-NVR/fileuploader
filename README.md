# Fileuploader

## Использование этого модуля клиентом
Данный модуль включает в себя 3 рута:

- https://nvr.miem.hse.ru/fileuploader/declare-upload
вы отправляете на данный адрес POST запорс с полями как в примере, вам возвращается id. По этому id загружаете дальше файлы вставляя его в url. Если ответ сервера 201, то всё хорошо

- https://nvr.miem.hse.ru/fileuploader/upload/{file_name}
вы отправляете на данный адрес PUT запросы с байтами или с файлами видео, согласно приведенному коду в конце README. Вместо file_id вы вставляете id, полученный по запросу в declare-upload. Возвращается код 200, если всё хорошо

### Пример кода для загрузки на сервер
```
    file_size = str(os.stat(file_path).st_size)
    dat = json.dumps(
        {
            "file_name": "zxc_file3",  # выираете имя на диске гугла
            "folder_name": "zxc",  # выбираете имя папки для загрузки. Папка находится в parent_id директории
            "parent_folder_id": "1weIs_vptfXVN20hSIpN9thL7Vh7VgH3h",  # сам parent_id
            "file_size": file_size,  # размер файла
        }
    )
    async with ClientSession() as session:
        async with session.post(
            f"{session_url}/declare-upload",
            data=dat,
        ) as resp:
            file_id = await resp.text()
            file_id = file_id.replace('"', "")

    async with AIOFile(file_path, "rb") as afp:
        file_size = str(os.stat(file_path).st_size)
        reader = Reader(afp, chunk_size=256 * 1024 * 100)  # загрузка по 25MB
        async for chunk in reader:
            async with ClientSession() as session:
                async with session.put(
                    f"{session_url}/upload/{file_id}", data={"file_in": chunk}
                ) as resp:
                    print(await resp.text())
```