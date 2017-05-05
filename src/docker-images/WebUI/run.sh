#!/bin/bash

cp /WebUI/userconfig.json .

dotnet restore
dotnet run
