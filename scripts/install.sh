set -e

export UV_PROJECT_ENVIRONMENT="$HOME/.venv-arrow"
export UV_LINK_MODE=copy
export UV_TRUSTED_HOST="$ARROW_TRUSTED_HOST"
export VIRTUAL_ENV="$HOME/.venv-arrow"
UV="$HOME/.local/bin/uv"
INSTALL_OPTS="--no-deps --index-url $ARROW_REGISTRY_URL --no-cache"
RESTART=1
for arg in "$@"; do
    case "$arg" in
        --no-restart) RESTART= ;;
        *) echo "unknown option: $arg" >&2; exit 1 ;;
    esac
done

if [ "$RESTART" ]; then
    supervisorctl stop arrow || true
fi

$UV pip install -r /tmp/pyproject.toml --no-sources --extra-index-url "$ARROW_REGISTRY_URL" --no-cache
$UV pip install arrow==0.0.1 --reinstall-package arrow $INSTALL_OPTS

if [ "$RESTART" ]; then
    supervisorctl start arrow
fi

tail -f /var/log/arrow.log
