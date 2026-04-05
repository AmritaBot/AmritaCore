cd ../
uv run pytest tests/ --cov=src/amrita_core --cov-report=term-missing --cov-report=xml --junitxml=test-results.xml -v
