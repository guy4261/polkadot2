#!/bin/bash

TARGET=~/.polkadot2.json

if [[ -f "${TARGET}" ]]; then
    echo "${TARGET} exists; aborting. You may delete and run again."
    exit 1
else
    cat << ENDL > ~/.polkadot2.json
{
    "repos": {
        "https://github.com/guy4261/polkadot2": "$(pwd)"
    }
}
ENDL
    echo "New ${TARGET} file created."
fi