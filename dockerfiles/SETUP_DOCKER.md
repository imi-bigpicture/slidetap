# Setup docker in wsl

## Instsall wsl

See <https://docs.microsoft.com/en-us/windows/wsl/install>

```console
wsl --install
```

Check that wsl is version 2:

```console
wsl -l -v
```

If it is not, upgrade with:

```console
wsl --set-version <distro name> 2
```

Start a wsl terminal by starting ubuntu through windows start meny.

## Install Docker engine

See <https://docs.docker.com/engine/install/ubuntu/>, "Install using the repository"

Try the docker installation with

```console
sudo docker run hello-world
```

If dockerd is not running, start it first:

```console
sudo dockerd
```

Configure docker to start on boot, see <https://docs.docker.com/engine/install/linux-postinstall/>.

## Install Docker compose

See instruction for linux on <https://docs.docker.com/compose/install/>

## Configure port forwardning

The host must forward the used port to localhost so that wsl/docker can recieve connections from outside. See step 3 and 4 <https://www.williamjbowman.com/blog/2020/04/25/running-a-public-server-from-wsl-2/>

```console
netsh interface portproxy add v4tov4 listenport=$SLIDES_PORT listenaddress=0.0.0.0 connectport=$SLIDES_PORT connectaddress=127.0.0.1
```

## Build

```console
docker compose build
```
