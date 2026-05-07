#!/usr/bin/env sh

echo "Initializing project environment, using uv..."

uv sync

# Freeze example files so local modifications are ignored by Git.
git update-index --skip-worktree src/examples/java/CodeWithSmell.java src/examples/java/CodeWithoutSmell.java src/examples/python/code_with_smell.py src/examples/python/code_without_smell.py 2>/dev/null

uv run pre-commit install

echo "Project environment initialized. You can now run the energy tracer using 'uv run ET'."
echo "For more information, please use the README.md file or run 'uv run ET --help' for usage instructions."