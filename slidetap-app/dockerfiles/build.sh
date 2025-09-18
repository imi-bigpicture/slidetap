rm *.zip *.tar

docker buildx build \
-t bigpicture_slidetap \
-f dockerfiles/bigpicture-slidetap.DockerFile \
--build-context slidetap-app=../slidetap/slidetap-app \
--build-context bigpicture_metadata_interface=../bigpicture_metadata_interface \
--build-context opentile=../opentile \
--build-context wsidicomizer=../wsidicomizer \
--build-context wsidicom=../wsidicom \
.


docker save bigpicture_slidetap > bigpicture_slidetap.tar
