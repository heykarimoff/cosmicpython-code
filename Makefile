# these will speed up builds, for docker-compose >= 1.25
export COMPOSE_DOCKER_CLI_BUILD=1
export COMPOSE_PROJECT_NAME=cosmicpython
export DOCKER_BUILDKIT=1

all: down build up test

build:
	docker-compose build

up:
	docker-compose up -d app

down:
	docker-compose down

logs:
	docker-compose logs --tail=100 app

test: up test-e2e test-integration test-unit

test-e2e:
	docker-compose run --rm --no-deps --entrypoint=pytest app /tests/e2e

test-integration:
	docker-compose run --rm --no-deps --entrypoint=pytest app /tests/integration

test-unit:
	docker-compose run --rm --no-deps --entrypoint=pytest app /tests/unit

check-black:
	black --line-length 80 --diff --check .

check-isort:
	isort . --check --diff

check-flake8:
	flake8 $(find * -name '*.py')
