# Download Cloud Configuration file in CoreOS boot image

* Please note that URL shortcut service such as aka.ms may not work in the CoreOS boot environment, you may need to use the full [CLOUD_CONFIG_URL] if you need to access it over the Internet.

* To access Internet from the CoreOS boot environment, you may need to edit /etc/resolv.conf file, and add a public name server, e.g., 

```
nameserver 8.8.8.8
```

Then, you can download the cloud config file from [CLOUD_CONFIG_URL] via wget. 