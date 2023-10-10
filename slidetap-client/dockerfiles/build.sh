rm *.zip *.tar

docker buildx build  -t slidetap-webserver -f dockerfiles/webserver.Dockerfile  .

docker save slidetap-webserver > slidetap-webserver.tar

zip slidetap-webserver.zip slidetap-webserver.tar
