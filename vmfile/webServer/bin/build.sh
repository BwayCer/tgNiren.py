#!/bin/bash
# 建立映像文件


##shStyle ###


__filename=`realpath "$0"`
_dirsh=`dirname "$__filename"`


vmFileItemDir=`dirname "$_dirsh"`
vmFileItemDirName=`basename "$vmFileItemDir"`
vmFileDir=`dirname "$vmFileItemDir"`
projectDir=`dirname "$vmFileDir"`


##shStyle 介面函式


fnBuild() {
    local mainVmfile="$vmFileItemDir/Dockerfile"
    local mainImgName="local/tg-niren:latest"

    ln -sf "$vmFileItemDir/.dockerignore" "$projectDir"

    docker build --network host -t "$mainImgName" -f "$mainVmfile" "$projectDir"
}


##shStyle ###


fnBuild "$@"

