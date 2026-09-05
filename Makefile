.PHONY: install lint format test run docker-build docker-up eval

install:
	pip install -e ".[dev]"

lint:
	ruff check .

format:
	ruff format .

test:
	pytest

run:
	python -m decp

eval:
	python eval/run.py

docker-build:
	docker build -t decp-copilot .

docker-up:
	docker compose up --build
