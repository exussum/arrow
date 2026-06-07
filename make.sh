#!/bin/sh

pip install '.[build]'
rm -rf dist
python3 -m build --wheel
python3 -m twine upload -u a -p a --repository-url http://registry.int.exussum.org dist/arrow-*.whl
