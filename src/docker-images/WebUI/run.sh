#!/bin/bash
rm --force userconfig.json
ln -s /WebUI/userconfig.json .
rm --force configAuth.json
ln -s /WebUI/configAuth.json .
rm --force Master-Templates.json
ln -s /WebUI/Master-Templates.json .
rm --force dashboardConfig.json
ln -s /WebUI/dashboardConfig.json .

dotnet restore
dotnet run
/bin/sleep infinity
