# Local Console

An offline tool to interact with IMX500-equipped smart cameras and develop applications for them. This software provides the following functionalities:

- Connection configuration
- Streaming control
- WASM Module deployment
- AI model deployment
- Camera firmware update

## Prerequisites

Ensure the following dependencies are installed on your system and added to your `PATH` environment variable:

* Python 3.11 or higher (including pip)
* [mosquitto](https://mosquitto.org/download)
* [flatc](https://github.com/google/flatbuffers/releases/tag/v24.3.25)

Ensure these programs are added to your system's `PATH` environment variable.

## Installation

The installation procedure depends on your machine. The details for each supported OS are outlined below.

> [!TIP]
> Make sure your machine has working Internet access, as all variants of the installation procedure will require downloading third-party dependencies.

### Windows

You should execute the `local-console-setup-*.exe` installer, as your regular (i.e. non-admin) user. For the installer to download the system dependencies, the installer will attempt to run a shell script as an Administrator, causing Windows' UAC to prompt for your permission to do so. Once the system dependencies are installed, another shell script will be executed as your user, installing the Local Console in your user account.

### Linux
Please note that Local Console for Linux is not actively tested/verified.

Currently, there is no stand-alone installer as there is for Windows. Hence, after fulfilling [the prerequisites](#prerequisites), perform the following steps:

Create a Python virtual environment:

```sh
$ python3.11 -m venv lcenv
$ . lcenv/bin/activate
```

Install Local Console using the provided Python wheel `local_console-*-py3-none-any.whl`:

```sh
(lcenv)$ pip install ./local_console-*-py3-none-any.whl
```

Or from the repository:

```sh
(lcenv)$ pip install -e local-console
```

The Local Console has been installed. To use it, either run the `local-console` command with the `lcenv` virtualenv activated, or use the absolute path to the `local-console` binary located in the `bin` subdirectory at the location of the `lcenv` virtualenv.

#### Mosquitto

By default, the mosquitto service runs on port 1883. You can check its status with:

```sh
systemctl status mosquitto.service
```

Make sure that its installation did not enable a running instance, by doing:

```sh
sudo systemctl disable mosquitto.service
sudo systemctl stop mosquitto.service
```

This action is only necessary once after installing the software.

### OSX

Please note that Local Console for OSX is not actively tested/verified.

The procedure is the same as for [Linux](#linux).

## Usage

Ensure the `lcenv` virtual environment is activated.

### Backend

Display help information:

```sh
(lcenv)$ local-console --help
```

### UI

Check its [README](local-console-ui/README.md).

## Logs

Logs from both the GUI and the backend are available at `$USERDATA/local-console/logs/main.log`.

* On Windows: `$USERDATA` is `%APPDATA%`
* On Linux: `$USERDATA` is `$HOME/.config`

## Guidelines

* [Build](docs/BUILD.md)
* [Development](DEVELOPMENT.md)
* [Contributing](CONTRIBUTING.md)
* [Code of Conducts](CODE_OF_CONDUCT.md)
