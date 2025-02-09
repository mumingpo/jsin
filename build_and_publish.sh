#!/bin/bash

set -euxo pipefail

rm -rd dist/

python -m build

python -m twine upload --verbose dist/*

