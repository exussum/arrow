#!/bin/sh

if [ ! -f scripts/deploy.env ]; then
    echo "scripts/deploy.env missing — copy scripts/deploy.env.example and set your hosts" >&2
    exit 1
fi
. scripts/deploy.env

if [ -n "$(git status --porcelain)" ]; then
    echo "Error: uncommitted changes present" >&2
    git status --short >&2
    exit 1
fi

rm -rf dist
uv build --wheel

export UV_PUBLISH_USERNAME=a
export UV_PUBLISH_PASSWORD=a
export UV_PUBLISH_URL="$ARROW_REGISTRY_URL"

uv publish dist/arrow-*.whl
