FROM python:3.8.5

COPY . /fileuploader

COPY ./requirements.txt /
RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir /root/temp_vids

EXPOSE 5500

WORKDIR /fileuploader/fileuploader

CMD ["python", "main.py"]
