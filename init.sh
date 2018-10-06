#! /bin/bash

rm -rf target
mkdir target

pushd target >/dev/null

mkdir environments
mkdir pipelines

popd >/dev/null

#echo -e "##\nTarget structure set-up:\n##"
#find target
