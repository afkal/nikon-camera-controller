.PHONY: run test lint format check

run:
	python app/main.py

test:
	pytest tests/ -v

lint:
	ruff check app/ tests/

format:
	black app/ tests/

check: lint test
