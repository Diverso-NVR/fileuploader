docker stop nvr_fileuploader
docker rm nvr_fileuploader
docker build -t nvr_fileuploader .
docker run -d \
 -it \
 --restart on-failure \
 --name nvr_fileuploader \
 --net=host \
 -p 5500:5500 \
 -v $HOME/creds:/nvr_fileuploader/creds \
 nvr_fileuploader
