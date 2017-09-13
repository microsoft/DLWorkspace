#!/bin/bash
rm --force userconfig.json
ln -s /WebUI/userconfig.json .
rm --force Master-Templates.json
ln -s /WebUI/Master-Templates.json .

dotnet restore
dotnet run
