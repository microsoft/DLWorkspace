Hostname "{{ HOST_NAME | default("collectd-docker") }}"

TypesDB "/usr/share/collectd/types.db"

FQDNLookup false
Interval 30
Timeout 2
ReadThreads 5

#LoadPlugin statsd
#LoadPlugin cpu
LoadPlugin network
LoadPlugin python
LoadPlugin df
LoadPlugin processes
LoadPlugin filecount

LoadPlugin disk
LoadPlugin dns

#<Plugin statsd>
#  Host "::"
#  Port "8125"
#  DeleteSets      true
#  TimerPercentile 90.0
#</Plugin>

<Plugin network>
  Server "{{ EP_HOST }}" "{{ EP_PORT }}"
  ReportStats true
</Plugin>

<Plugin "python">
    ModulePath "/usr/lib/collectd"
    Interactive False		
    Import "cuda_collectd"
    LogTraces true
</Plugin>


<Plugin "python">
    ModulePath "/usr/lib/collectd"
    Interactive False		
    Import "kubernetes_collectd"
    LogTraces true
</Plugin>

<Plugin "processes">
    ProcessMatch "kubelet" "kubelet"
</Plugin>


<Plugin "df">
  FSType "/^(cifs|nfs|ext4|ext3)/"
  MountPoint "/^(/hostfs|/hostfs/mntdlws/.*)$/"
</Plugin>


<Plugin "filecount">
  <Directory "/hostfs/var/log">
    Instance "var-log"
  </Directory>
</Plugin>
