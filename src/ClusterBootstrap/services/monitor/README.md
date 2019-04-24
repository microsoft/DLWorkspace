# How to deploy

Before deploy monitor services, we need to first generate the configmap of grafana, this configmap contains several dashboards and data source needed by grafana service.

To generate the configmap file, run command

```
services/monitor/gen-grafana-config.sh
```

This will read dashboard files from `services/monitor/grafana-config` directory and generate `services/monitor/grafana-config.yaml` file. After this step you can run normal

```
./deploy.py kubernetes start monitor
```

to start monitor services.
