#!/bin/sh

pip install '.[build]'
rm -rf dist
python3 -m build --wheel
python3 -m twine upload --repository-url http://registry.int.exussum.example dist/arrow-*.whl
