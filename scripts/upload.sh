#!/bin/sh

if [ -n "$(git status --porcelain)" ]; then
    echo "Error: uncommitted changes present" >&2
    git status --short >&2
    exit 1
fi

printf 'SHA = "%s"\nBUILD_TIME = "%s"\n' "$(git rev-parse --short HEAD)" "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" > src/arrow/_build.py
rm -rf dist
uv pip install '.[build]'
uv build --wheel
uv run --no-sync twine upload -u a -p a --repository-url http://registry.int.exussum.org dist/arrow-*.whl
git checkout src/arrow/_build.py
