#!/bin/bash
rm --force userconfig.json
ln -s /WebUI/userconfig.json .

dotnet restore
dotnet run
