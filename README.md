# cosmicpython-code
Example application code for the [Architecture Patterns with Python](https://www.oreilly.com/library/view/architecture-patterns-with/9781492052197/) book.

[![Python app workflow](https://github.com/heykarimoff/cosmicpython-code/actions/workflows/python-app.yml/badge.svg?branch=master)](https://github.com/heykarimoff/cosmicpython-code/actions/workflows/python-app.yml)
[![DeepSource](https://deepsource.io/gh/heykarimoff/cosmicpython-code.svg/?label=active+issues&show_trend=true&token=Q8CoowvMEAg9gbFgHrXaVOmX)](https://deepsource.io/gh/heykarimoff/cosmicpython-code/?ref=repository-badge)

Visit [API documentation](https://documenter.getpostman.com/view/14594760/Tz5iA1Vc) to see available endpoints.

### Installation
Install dependencies:
```sh
pip install -r requirements.txt
```

### Tests
Run all tests:
```sh
make test
```
Run only unit tests:
```sh
make test-unit
```
Run only integration tests:
```sh
make test-integration
```
Run only end-to-end tests:
```sh
make test-e2e
```
Run only smoke tests:
```sh
make test-smoke
```
