#!/bin/sh

if [ -n "$(git status --porcelain)" ]; then
    echo "Error: uncommitted changes present" >&2
    git status --short >&2
    exit 1
fi

rm -rf dist
uv build --wheel

export UV_PUBLISH_USERNAME=a
export UV_PUBLISH_PASSWORD=a
export UV_PUBLISH_URL=http://registry.int.exussum.org

uv publish dist/arrow-*.whl
