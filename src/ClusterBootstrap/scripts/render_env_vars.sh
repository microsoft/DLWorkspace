#!/bin/bash
set -ex
src=$1
dst=$2
varname=$3
val="${!varname}"
sed 's/$'$varname'/'"$val"'/g' $src > $src".rendred"
sudo cp $src".rendred" $dst