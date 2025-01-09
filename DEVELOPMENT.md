# Development Guide

Before submitting a pull request, or a change to an existing one, please make sure to perform the following actions.

## General

Ensure code style consistency across the project by running the linter:

```sh
(lcenv)$ pre-commit run --all-files
```

## Backend

### Run Unit Tests

Execute the backend unit tests using Pytest:

```sh
(lcenv)$ pytest tests/
```

If you want to capture coverage data,

```sh
(lcenv)$ coverage run -m pytest tests -o junit_family=xunit1 --junitxml=xunit-result.xml
(lcenv)$ coverage xml
```

## UI

From `local-console-ui` directory,

### Code Formatting

```
yarn format
```

This command runs the formatter to ensure that your code adheres to the project's coding standards.

### Unit tests

Run unit tests using Jest:

```sh
yarn test
```

### E2E tests (playwright)

#### Prerequisites

Install mocked device from root of the repository,

```sh
(lcenv)$ pip install -e ../mocked-device
```

#### Run E2E tests

```sh
(lcenv)$ ./ui-tests/run-e2e.sh
```

This leverages the file `scripts/launch-ui-tests.js` to start both the app and tests.

The tests produce reports, both to `stdout` and to `./ui-tests/report/index.html`.
