#!/bin/bash
if lspci | grep -qE "[0-9a-fA-F][0-9a-fA-F]:[0-9a-fA-F][0-9a-fA-F].[0-9] (3D|VGA compatible) controller: NVIDIA Corporation.*"; then
  /opt/install_nvidia_driver.sh || exit $?
  echo NVIDIA gpu detected, drivers installed
else
  echo NVIDIA gpu not detected, skipping driver installation
fi