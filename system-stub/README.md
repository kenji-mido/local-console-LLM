# System stub

This project is a temporary workaround
to demonstrate the functionalities
of local-console with RaspberryPI
and its Picamera.

It is based on mocked-device library
which embeds some of its features.

# Debian package

## Pre-requisites

Install the required dependencies
to build the debian package.

```sh
sudo apt install python3 python3-pip python3-venv
```

## Create package

Create the debian package
with a simple make command:

```sh
make
```

## Installation

System app is emulated using the `evp-agent`
together with `system-stub`.

So `evp-agent` should be installed as well,
although there are no inter dependencies.
Refer to [edge-virtualization-platform](https://github.com/SonySemiconductorSolutions/edge-virtualization-platform).

```sh
sudo apt install ./system-stub_*.deb
```

## Service

After installing the package,
configure services by editing
`/etc/system-app/env.conf`,
and edit `EVP_MQTT_HOST` and `EVP_MQTT_PORT` env vars
with the host and port of the broker
the agent and system-stub shall connect to.

```ini
EVP_MQTT_HOST=localhost
EVP_MQTT_PORT=1883
```

Then enable services rules
to start services at boot:

```sh
sudo systemctl enable evp-agent.service
sudo systemctl enable system-stub.service
```

And eventually start them:

```sh
sudo systemctl start evp-agent.service
sudo systemctl start system-stub.service
```
