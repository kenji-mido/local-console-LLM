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

### Frontend tests (Playwright)

These tests mock the backend (REST API) and focus only on testing the UI.

```sh
(lcenv)$ yarn test:fe
```

The tests generate reports, both to `stdout` and in `./reports`.

### E2E tests (Playwright)

These tests use the real backend and can run with either a real or a mocked device.

#### Prerequisites

Install mocked device from root of the repository,

```sh
(lcenv)$ pip install -e ../mocked-device
```

#### Run E2E tests

To run tests with a **mocked device**:

```sh
(lcenv)$ yarn test:e2e-vx
```

> `vx` is one of `v1` or `v2` for the corresponding Edge-Cloud Interface

To run tests with a **real device**, make sure:

1. Set up the device to connect to the IP address where the tests will run.
2. Download necessary sample files.

Use the following Docker command to download and extract the required sample files:

```sh
./local-console-ui/scripts/download-assets.sh
```

After setting up the device and downloading the sample files, run the following command, replacing ${IP_ADDRESS} with the actual IP address of the MQTT broker:

```sh
(lcenv)$ DEVICE_TYPE=real IP_ADDRESS=${IP_ADDRESS} yarn test:e2e-vx
```

> `vx` is one of `v1` or `v2` for the corresponding Edge-Cloud Interface

##### Parameters

You can control the test setup with the following environment variables:

- **DEVICE_TYPE**: `real` | `mocked` (default)
  - `mocked`: Uses a mock device for testing.
  - `real`: Uses an actual device connected to the Local Console MQTT broker.
- **IP_ADDRESS**: Required when using a real device. Specify the IP address of the MQTT broker.

##### Choosing Specific Tests

You can filter or skip specific tests using Playwright's test annotations. For example, to skip tests tagged @slow, use the following flag:

```sh
--grep-invert @slow
```

For more about Playwright test annotations, refer to the [Playwright documentation](https://playwright.dev/docs/test-annotations#tag-tests).

##### Optional Flags

To run tests in Playwright’s interactive UI mode, add the `--ui` flag:

```sh
yarn test:e2e-vx --ui
```

where `vx` is one of `v1` or `v2` for the corresponding Edge-Cloud Interface

##### Notes on E2E Tests

E2E tests take longer to run because they start the backend for each test. If using a real device, it takes even more time as the interactions are not simulated. If you only need to test the UI, it is better to use frontend tests.
