1. Map NICs to container:

```
root@10:/notebooks# iperf -c 10.196.46.54
------------------------------------------------------------
Client connecting to 10.196.46.54, TCP port 5001
TCP window size: 45.0 KByte (default)
------------------------------------------------------------
[  3] local 10.196.45.233 port 55920 connected with 10.196.46.54 port 5001
[ ID] Interval       Transfer     Bandwidth
[  3]  0.0-10.0 sec  10.9 GBytes  9.38 Gbits/sec
root@10:/notebooks# iperf -c 10.196.46.54
------------------------------------------------------------
Client connecting to 10.196.46.54, TCP port 5001
TCP window size: 45.0 KByte (default)
------------------------------------------------------------
[  3] local 10.196.45.233 port 55922 connected with 10.196.46.54 port 5001
[ ID] Interval       Transfer     Bandwidth
[  3]  0.0-10.0 sec  10.9 GBytes  9.39 Gbits/sec
root@10:/notebooks# iperf -c 10.196.46.54
------------------------------------------------------------
Client connecting to 10.196.46.54, TCP port 5001
TCP window size: 45.0 KByte (default)
------------------------------------------------------------
[  3] local 10.196.45.233 port 55924 connected with 10.196.46.54 port 5001
[ ID] Interval       Transfer     Bandwidth
[  3]  0.0-10.0 sec  10.9 GBytes  9.39 Gbits/sec
```


2. service port forward: (start a service on kubernetes. the service finds an available host ports and forward to a container port.)

```
root@worker2-js4ng:/notebooks# iperf -c 10.196.46.23 -p 30722
------------------------------------------------------------
Client connecting to 10.196.46.23, TCP port 30722
TCP window size: 45.0 KByte (default)
------------------------------------------------------------
[  3] local 10.2.80.2 port 33046 connected with 10.196.46.23 port 30722
[ ID] Interval       Transfer     Bandwidth
[  3]  0.0-10.0 sec  3.37 GBytes  2.90 Gbits/sec
root@worker2-js4ng:/notebooks# iperf -c 10.196.46.23 -p 30722
------------------------------------------------------------
Client connecting to 10.196.46.23, TCP port 30722
TCP window size: 45.0 KByte (default)
------------------------------------------------------------
[  3] local 10.2.80.2 port 33048 connected with 10.196.46.23 port 30722
[ ID] Interval       Transfer     Bandwidth
[  3]  0.0-10.0 sec  3.38 GBytes  2.90 Gbits/sec
root@worker2-js4ng:/notebooks# iperf -c 10.196.46.23 -p 30722
------------------------------------------------------------
Client connecting to 10.196.46.23, TCP port 30722
TCP window size: 45.0 KByte (default)
------------------------------------------------------------
[  3] local 10.2.80.2 port 33050 connected with 10.196.46.23 port 30722
[ ID] Interval       Transfer     Bandwidth
[  3]  0.0-10.0 sec  3.44 GBytes  2.95 Gbits/sec
```


3. flanneld: directly communication between pods. 

```
root@worker2-js4ng:/notebooks# iperf -c 10.2.19.3 -p 2222
------------------------------------------------------------
Client connecting to 10.2.19.3, TCP port 2222
TCP window size: 45.0 KByte (default)
------------------------------------------------------------
[  3] local 10.2.80.2 port 43904 connected with 10.2.19.3 port 2222
[ ID] Interval       Transfer     Bandwidth
[  3]  0.0-10.0 sec  6.55 GBytes  5.62 Gbits/sec
root@worker2-js4ng:/notebooks# iperf -c 10.2.19.3 -p 2222
------------------------------------------------------------
Client connecting to 10.2.19.3, TCP port 2222
TCP window size: 45.0 KByte (default)
------------------------------------------------------------
[  3] local 10.2.80.2 port 43906 connected with 10.2.19.3 port 2222
[ ID] Interval       Transfer     Bandwidth
[  3]  0.0-10.0 sec  6.36 GBytes  5.47 Gbits/sec
root@worker2-js4ng:/notebooks# iperf -c 10.2.19.3 -p 2222
------------------------------------------------------------
Client connecting to 10.2.19.3, TCP port 2222
TCP window size: 45.0 KByte (default)
------------------------------------------------------------
[  3] local 10.2.80.2 port 43908 connected with 10.2.19.3 port 2222
[ ID] Interval       Transfer     Bandwidth
[  3]  0.0-10.0 sec  6.70 GBytes  5.76 Gbits/sec
```
