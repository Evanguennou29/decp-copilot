.PHONY: install lint format test run ingest index serve mcp docker-build docker-up eval

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

ingest:
	python -m decp ingest

index:
	python -m decp index

serve:
	python -m decp serve

mcp:
	python mcp/server.py

eval:
	python eval/run.py

docker-build:
	docker build -t decp-copilot .

docker-up:
	docker compose up --build
