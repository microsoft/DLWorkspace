#!/bin/bash 
while true;
do
  ping -c1 google.com;
  if [ $? = 0 ]; then 
    echo "Success to connect to Internet at $(date)"
  else
    echo "Failed to connect to Internet at $(date)"
  fi
  sleep 10

done

