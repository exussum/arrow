if [ ! -f scripts/deploy.env ]; then
    echo "scripts/deploy.env missing — copy scripts/deploy.env.example and set your hosts" >&2
    exit 1
fi
. scripts/deploy.env
DEPLOY="${ARROW_DEPLOY_USER:-root}@$ARROW_DEPLOY_HOST"
CTRL="-o ControlMaster=auto -o ControlPath=/tmp/arrow-ssh-%r@%h:%p -o ControlPersist=60"
sh scripts/upload.sh "$1" \
    && ssh $CTRL "$DEPLOY" true \
    && scp $CTRL pyproject.toml "$DEPLOY:/tmp/pyproject.toml" \
    && ssh $CTRL "$DEPLOY" "ARROW_REGISTRY_URL='$ARROW_REGISTRY_URL' ARROW_TRUSTED_HOST='$ARROW_TRUSTED_HOST' bash -s" < scripts/install.sh
