#!/bin/bash

set -euxo pipefail

if [ -d dist ]
then
    rm -rd dist/
fi

python -m build

python -m twine upload --verbose dist/*

