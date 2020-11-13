# Fileuploader

## Использование этого модуля клиентом
Данный модуль включает в себя 3 рута:

- https://git.miem.hse.ru/nvr/fileuploader/declare-upload
вы отправляете на данный адрес GET запорс, вам возвращается id. Это имя пустого файла на сервере

- https://git.miem.hse.ru/nvr/fileuploader/upload/{file_name}
вы отправляете на данный адрес PUT запросы с байтами или с файлами видео, согласно приведенному коду в конце README. Вместо file_name вы вставляете id, полученный по запросу в declare-upload. Возвращается код 200, если всё хорошо

- https://git.miem.hse.ru/nvr/fileuploader/declare-stop/{file_name}
когда вы завершили загрузку видео и получили все ответы '200', вы отправляете на данный адрес POST запрос, где вместо file_name вы вставляете id, полученный по запросу в declare-upload. В теле запроса вы передаёте имя, которое будет иметь файл на гугл диске и имя папки, которая лежит в директории Zoom. Если папки с таким именем нет, то она создастся. То есть тело запроса должно иметь такую форму

    file_name: str
    
    folder_name: str

### Пример кода для PUT запроса
```
file = open('/home/sergey/Desktop/xaa', 'rb')

a = file.read()

file.close() 

files = {'file_in': ('some_name', a, 'video/mp4')}

r = requests.put(URL,files=files)
```