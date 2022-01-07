# these will speed up builds, for docker-compose >= 1.25
export COMPOSE_DOCKER_CLI_BUILD=1
export COMPOSE_PROJECT_NAME=cosmicpython
export DOCKER_BUILDKIT=1

all: down build up test

build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

logs:
	docker-compose logs --tail=100

test: up test-e2e test-integration test-unit

test-coverage: up coverage

test-e2e:
	docker-compose run --rm --no-deps --entrypoint=pytest app /tests/e2e -vv -rs

test-integration:
	docker-compose run --rm --no-deps --entrypoint=pytest app /tests/integration -v -rs

test-unit:
	docker-compose run --rm --no-deps --entrypoint=pytest app /tests/unit -v -rs

test-smoke:
	docker-compose run --rm --no-deps --entrypoint=pytest app /tests -vv -rs -m smoke

coverage:
	docker-compose run --rm --no-deps --entrypoint=pytest app /tests -q -rs --cov=allocation --cov-report xml:coverage.xml

check-black:
	black --line-length 80 --diff --check .

check-isort:
	isort . --check --diff

check-flake8:
	flake8 $(find * -name '*.py') --count --select=E9,F63,F7,F82 --show-source --statistics
	flake8 $(find * -name '*.py') --count --exit-zero --max-complexity=10 --max-line-length=80 --statistics
