#!/usr/bin/env sh

echo "Initializing project environment, using uv..."

uv sync

echo "Project environment initialized. You can now run the energy tracer using 'uv run ET'."
echo "For more information, please use the README.md file or run 'uv run ET --help' for usage instructions."