#!/bin/bash

__filename=`realpath "$0"`
_dirsh=`dirname "$__filename"`
projectDir=`realpath "$_dirsh/../../.."`
docker build --network host \
    -t "local/test/tg-tool/get-participants:latest" \
    -f "$_dirsh/Dockerfile" "$projectDir"

