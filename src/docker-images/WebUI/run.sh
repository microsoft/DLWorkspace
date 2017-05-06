#!/bin/bash
rm userconfig.json
ln -s /WebUI/userconfig.json .

dotnet restore
dotnet run
