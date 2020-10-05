#!/bin/bash
# 編譯 K8s 文件


##shStyle ###


set -e


##shStyle 介面函式


fnK8sketch() {
    local k8sDir="$1"

    local valueTxt=""
    local valuesYmlFilePath="$k8sDir/values.yml"
    [ ! -f "$valuesYmlFilePath" ] ||
        valueTxt="`grep "^# var [A-Za-z0-9_-]\+ .*$" "$valuesYmlFilePath"`"

    local compileYmlFilePath k8sYmlTxt
    find "$k8sDir" -maxdepth 1 -regextype sed -regex ".*\.sketch\.\(yml\|yaml\)" |
        while read ymlFilePath
        do
            compileYmlFilePath="`
                sed "s/\.sketch\(\.\(yml\|yaml\)\)$/\1/" <<< "$ymlFilePath"
            `"
            [ "$ymlFilePath" != "$valuesYmlFilePath" ] || continue

            k8sYmlTxt=`cat "$ymlFilePath"`
            while read line
            do
                fnTmpCutList $line
                key=${rtnTmpCutList[2]}
                value=`sed 's/\([&\/]\)/\\\\\1/g' <<< "${rtnTmpCutList[@]:3}"`

                k8sYmlTxt=`sed "s/\\\${$key}/$value/g" <<< "$k8sYmlTxt"`
            done <<< "$valueTxt"
            echo "$k8sYmlTxt" > "$compileYmlFilePath"
        done
}


##shStyle 函式庫


rtnTmpCutList=()
fnTmpCutList() {
    rtnTmpCutList=("$@")
}


##shStyle ###


fnK8sketch "$@"

