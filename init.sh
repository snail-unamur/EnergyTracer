#!/usr/bin/env sh

echo "Initializing project environment, using uv..."

uv sync

echo "Project environment initialized. You can now run the main script using 'uv run src/main.py'."
echo "For more information, please use the README.md file or run 'uv run src/main.py --help' for usage instructions."