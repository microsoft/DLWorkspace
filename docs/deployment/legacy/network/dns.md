# Add DNS server.

# https://unix.stackexchange.com/questions/128220/how-do-i-set-my-dns-when-resolv-conf-is-being-overwritten

sudo vim /etc/resolvconf/resolv.conf.d/base

Then put your nameserver list in like so:

nameserver 8.8.8.8
nameserver 8.8.4.4

sudo resolvconf -u
