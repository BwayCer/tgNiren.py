#!/bin/bash


pipenvRunSrc___filename=`realpath "$0"`
pipenvRunSrc__dirsh=`dirname "$pipenvRunSrc___filename"`

projectDir=`realpath "$pipenvRunSrc__dirsh/.."`

export PIPENV_PIPFILE="$projectDir/Pipfile"
cd "$projectDir/src"
pipenv run python -m asyncio

