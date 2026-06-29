#!/bin/sh

if [ -n "$(git status --porcelain)" ]; then
    echo "Error: uncommitted changes present" >&2
    git status --short >&2
    exit 1
fi

rm -rf dist
uv pip install '.[build]'
uv build --wheel
uv run --no-sync twine upload -u a -p a --repository-url http://registry.int.exussum.org dist/arrow-*.whl
