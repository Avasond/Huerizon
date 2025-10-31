.PHONY: setup test lint format

setup:
	python -m pip install -U pip wheel setuptools
	python -m pip install -r requirements-dev.txt

test:
	pytest --tb=short -q

lint: format
	ruff check .

format:
	ruff check . --fix