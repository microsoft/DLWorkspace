#!/bin/bash
src=$1
dst=$2
dirdst=$(dirname $dst)
# echo $USER
if [ ! -z "$dirdst" ]; then
	sudo mkdir -p $dirdst
	sudo chown -R $USER:$USER $dirdst
fi;
sudo cp $src $dst