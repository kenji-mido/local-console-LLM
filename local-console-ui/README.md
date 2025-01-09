# Local Console UI

> [!NOTE]
> All commands below assume:
> 1. You are in the `local-console-ui` directory.
> 2. Python virtual environment (`lcenv`) is activated.

## Running the Pre-built AppImage (Linux Only)

As part of GitHub Releases, we provide the Local Console UI as a pre-built AppImage compatible with x86-64 Linux systems. This allows you to run the application directly without installing any dependencies.

```sh
(lcenv)$ chmod +x LocalConsole-linux-x86_64.AppImage
(lcenv)$ ./LocalConsole-linux-x86_64.AppImage
```

Some Linux distributions may require `libfuse2`. If necessary, install it using your package manager.

## Installation

Before starting, install all necessary dependencies,

```sh
yarn install
```

## Development

To develop the UI, you'll need to run both the backend server and the UI in development mode.

### Start the Backend

From the root directory, with your Python virtual environment (`lcenv`) activated, start the backend server:

```sh
(lcenv)$ local-console -v serve
```

Alternatively, if you prefer to use a mock server:

```sh
yarn start:server
```

This uses a lightweight ExpressJS mock server located at ./server-mock for testing UI functionality without the full backend.

### Start the UI

In a new terminal window, run:

```sh
(lcenv)$ yarn start
```

This launches the UI in development mode with live reloading, suitable for development and testing.

## Production Build

The application is packaged and bundled using Electron, which compiles the Local Console UI into a standalone desktop application with all necessary dependencies.

### Building

```sh
yarn build:electron
```

The resulting executable is located in the `dist` directory.

### Running

After building, you can run the executable directly. For example, on Linux:

```sh
(lcenv)$ ./dist/LocalConsole-linux-x86_64.AppImage
```

### Build and Run in one command

For convenience, you can use a single command to build and run,

```sh
(lcenv)$ yarn start:electron
```
