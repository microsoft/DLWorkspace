#!/bin/bash

# Build a development docker dev:latest

docker build -t dev:latest .
docker run -ti --rm -v $HOME:$HOME dev:latest /bin/bash