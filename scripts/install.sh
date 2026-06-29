curl -sSL https://raw.githubusercontent.com/exussum/arrow/main/pyproject.toml -o /tmp/pyproject.toml
UV_PROJECT_ENVIRONMENT=/root/.venv-arrow UV_LINK_MODE=copy UV_TRUSTED_HOST=registry.int.exussum.org /root/.local/bin/uv sync --no-install-project --no-cache --directory /tmp
supervisorctl stop arrow
VIRTUAL_ENV=/root/.venv-arrow /root/.local/bin/uv pip install arrow==0.0.1 --no-deps --reinstall-package arrow --link-mode=copy --index-url http://registry.int.exussum.org --trusted-host registry.int.exussum.org --no-cache
supervisorctl start arrow
tail -f /var/log/arrow.log
