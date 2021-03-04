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

test:
	pytest --tb=short

format:
	black -l 80 $(find * -name '*.py')

lint:
	isort $(find * -name '*.py') --check --diff
	flake8 $(find * -name '*.py')
