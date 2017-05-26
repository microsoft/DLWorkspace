#!/bin/bash
set -e

if id -u REDMOND.hongzl 1>null 2>null ; then echo "joined domain" ; else echo $DOMAINPASSWD | net ads join -U $DOMAINUSER; fi
service winbind restart
service smbd restart

apachectl -e info -DFOREGROUND