FROM python:3.8.5

WORKDIR /file_uploader

COPY . /file_uploader
COPY routes/routes.py /file_uploader/routes/routes.py
COPY ./requirements.txt /

RUN mkdir /root/temp_vids

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5005


CMD ["uvicorn", "main:app",  "--port", "5005"]
