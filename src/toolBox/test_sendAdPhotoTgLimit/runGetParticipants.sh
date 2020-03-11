#!/bin/bash

__filename=`realpath "$0"`
_dirsh=`dirname "$__filename"`
projectDir=`realpath "$_dirsh/../../.."`
docker run --rm -it -v "$projectDir:/app" --network host "local/test/tg-tool/get-participants:latest" \
    python "/app/src/tool.py" "testSendAdPhotoTgLimit.getParticipants" "$@"

