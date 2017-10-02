Hostname "{{ HOST_NAME | default("collectd-docker") }}"

FQDNLookup false
Interval 10
Timeout 2
ReadThreads 5

LoadPlugin statsd
LoadPlugin cpu
LoadPlugin write_graphite

<Plugin statsd>
  Host "::"
  Port "8125"
  DeleteSets      true
  TimerPercentile 90.0
</Plugin>

<Plugin "write_graphite">
 <Node "endpoint">
   Host "{{ EP_HOST }}"
   Port "{{ EP_PORT }}"
   Protocol "tcp"
   LogSendErrors true
   EscapeCharacter "_"
   Prefix "{{ PREFIX | default("local.debug.") }}"
 </Node>
</Plugin>
