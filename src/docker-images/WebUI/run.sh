#!/bin/bash
rm -r /DLWorkspace
ssh-keyscan github.com >> /root/.ssh/known_hosts
ssh-agent bash -c 'ssh-add /root/.ssh/id_rsa; git clone -b webUI git@github.com:MSRCCS/DLWorkspace.git /DLWorkspace'

cp WebUI/appsettings.json /DLWorkspace/src/WebUI/dotnet/WebPortal/appsettings.json

cd /DLWorkspace/src/WebUI/dotnet/WebPortal
dotnet restore
dotnet run
