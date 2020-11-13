FROM python:3.8.5

WORKDIR /file_uploader

COPY . /file_uploader
COPY ./requirements.txt /
RUN mkdir /bin_for_temp_vids
RUN mkdir logging
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5005


CMD ["uvicorn", "main:app",  "--port", "5005"]
