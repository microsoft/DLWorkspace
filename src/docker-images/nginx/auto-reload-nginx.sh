#!/bin/sh

# Copyright 2016 The Kubernetes Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Please put the fully qualifed domain name of the node that the docker runs upon at /etc/hostname-fqdn

# If you only have http access, you can use certbot certonly --webroot -w /usr/share/nginx/ -d $fqdn to obtain certificate
# 
fqdn=`cat /etc/hostname-fqdn`
command='s/hostname-fqdn/'$fqdn'/'
sed $command -i /etc/nginx/conf.d/default.conf
echo sed $command -i /etc/nginx/conf.d/default.conf
# cp /etc/nginx/nginx.before_cert.conf /etc/nginx/nginx.conf
# nginx "$@"
certbot --installer nginx --authenticator standalone -n --agree-tos -m dlworkspace@gmail.com --domain $fqdn --pre-hook "nginx -s stop" --post-hook "nginx"
# ./certbot-auto run --nginx -n --agree-tos -m dlworkspace@gmail.com --domain $fqdn
# cp /etc/nginx/nginx.after_cert.conf /etc/nginx/nginx.conf
# nginx "$@"

oldcksum=`cksum /etc/nginx/conf.other/default.conf`

inotifywait -e modify,move,create,delete -mr --timefmt '%d/%m/%y %H:%M' --format '%T' \
/etc/nginx/conf.other/ | while read date time; do

	newcksum=`cksum /etc/nginx/conf.other/default.conf`
	if [ "$newcksum" != "$oldcksum" ]; then
		echo "At ${time} on ${date}, config file update detected."
		oldcksum=$newcksum
		nginx -s reload
	fi

done