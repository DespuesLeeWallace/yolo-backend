.PHONY: install test run build docker-run lint clean

install:
	uv sync

test:
	uv run python tests/run_all.py

run:
	uv run python main.py

build:
	docker build -t yolo-backend .

docker-run:
	docker run --rm --env-file .env.local yolo-backend

lint:
	uv run python -m py_compile main.py
	uv run python -m py_compile src/database.py
	uv run python -m py_compile src/scrapers/resident_advisor.py
	uv run python -m py_compile src/scrapers/fever.py
	uv run python -m py_compile src/scrapers/songkick.py
	uv run python -m py_compile src/scrapers/xceed.py
	@echo "All files compile OK"

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache
