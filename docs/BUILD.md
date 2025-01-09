# Building Local Console

Ensure all dependencies are installed before building.

## Backend

With a Python 3.11+ environment,

```sh
$ pip install build
$ python -m build local-console --wheel
```

The wheel is generated at `local-console/dist`.

## UI

From `local-console-ui`,

```sh
yarn build:electron
```

The executable is generated in `local-console-ui/dist`.
