#!/bin/bash
# a quick and easy way to display a btor file in a (more) homan readable way

path=`dirname "$0"`
cmd="java -cp ${path}/target/scala-2.13/bug-fix-synthesizer-assembly-0.1.jar BtorViewer ${@:1}"
eval $cmd
