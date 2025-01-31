---
title: Example
layout: home
nav_order: 2
---

# SlideTap example

SlideTap includes a simple example application that can be run in Docker. This page details how to setup and run the example application. The instructions are for Ubuntu, but other distributions of Linux should also work with some modifications.


## Clone the repository

Cloning the repository is easiest done with git, which can be installed with:

```sh
sudo sudo apt-get update
sudo apt-get install git
```

Next, cd to a working directory and clone the repository:

```sh
git clone https://github.com/imi-bigpicture/slidetap.git
```

All the subsequent commands should be executed in the `slidetap/example` folder:

```sh
cd slidetap/example
```

## Prepare example data

The example application uses test images from [Cytomine collection](https://cytomine.com/collection/cmu-1/cmu-1-svs). The python script "prepare-example-data.py" downloads the images to the expected folder.

```sh
python prepare-example-data.py
```

This will create the following folder structure:

```sh
ls -R storage/images/
storage/images/:
>> ABC-1+2-A-1  ABC-1+2-A-2
>>
>> storage/images/ABC-1+2-A-1:
>> ABC-1+2-A-1.svs
>>
>> storage/images/ABC-1+2-A-2:
>> ABC-1+2-A-2.svs
```

## Prepare ssl certificate

SSL certificates are needed for the Docker web server. One can use the "snakeoil" certificates in the "ssl-cert":

First install ssl-cert:

```sh
sudo sudo apt-get update
sudo apt-get install ssl-cert
```

Then create certificates:

```sh
sudo python prepare-example-ssl.py
```

This will create the following folder structure:

```sh
ls ssl/
>> cert.pem  privkey.pem
```

## Prepare configuration

To run SlideTap you need both an `.env`-file (parsed by Docker) and a `config.yaml`-file (parsed by the Python applications). You can create these with the provide Python cli-script:

```sh
python prepare-example-config.py
```

This will create `.env`-file:

```sh
cat .env
>> SLIDETAP_SERVERNAME=localhost
>> SLIDETAP_PORT=3000
>> SLIDETAP_STORAGE=/mnt/c/work/SlideTap/example/storage
>> SLIDETAP_APIPORT=10000
>> SLIDETAP_CONFIG_FILE=/storage/config.yaml
>> SLIDETAP_WEB_APP_CREATOR=slidetap.apps.example.web_app:create_app()
>> SLIDETAP_TASK_APP=slidetap.apps.example.task_app:task_app
>> SLIDETAP_SSL_CERTIFICATE_FOLDER=/mnt/c/work/SlideTap/example/ssl
>> SLIDETAP_SSL_CERTIFICATE=cert.pem
>> SLIDETAP_SSL_CERTIFICATE_KEY=privkey.pem
>> SLIDETAP_EXAMPLE_TEST_DATA=/storage/images
>> SLIDETAP_SECRET_KEY=DEVELOP
>> SLIDETAP_WEBAPP_URL=localhost:3000
```

Where the `SLIDETAP_STORAGE` and `SLIDETAP_SSL_CERTIFICATE_FOLDER` will depend on the example folder.

and `config.yaml`-file:

```sh
cat storage/config.yaml
>> celery:
>>   concurrency: null
>>   max_tasks_per_child: 10
>> dicomization:
>>   levels: all
>>   threads: 1
>> enforce_https: false
>> keepalive: 1800
>> log_level: DEBUG
```

## Installing docker

See <https://docs.docker.com/engine/install/ubuntu/>, "Install using the repository"

Try the docker installation with

```console
sudo docker run hello-world
```

If dockerd is not running, start it first:

```console
sudo dockerd
```

## Install Docker compose

See instruction for linux on <https://docs.docker.com/compose/install/>

## Build with docker compose

Run docker compose build to build needed images:

```sh
sudo docker compose build
```

## Run with docker compose

Run docker compose run to start the SlideTap container:

```sh
sudo docker compose run
```

## Browse

Navigate to the SlideTap server url (default `https://localhost:3000/`). Login with `test`/`test`. Create a project using the `input.json` file located in `SlideTap/slidetap-app/tests/test_data`.
