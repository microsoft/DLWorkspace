import React, {
  ChangeEvent,
  FunctionComponent,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState
} from 'react';
import {
  each,
  filter,
  map,
  mapValues
} from 'lodash';
import {
  Card,
  CardMedia,
  Link,
  MenuItem,
  Select,
  Tooltip,
  Typography,
  makeStyles
} from '@material-ui/core';
import {
  Column,
  Options,
  DetailPanel
} from 'material-table';

import SvgIconsMaterialTable from '../../components/SvgIconsMaterialTable';
import TeamContext from '../../contexts/Team';
import useTableData from '../../hooks/useTableData';
import usePrometheus from '../../hooks/usePrometheus';

import useResourceColumns, { ResourceKind } from '../Clusters/useResourceColumns';
import QueryContext from './QueryContext';

interface Props {
  data: any;
}

const useLinkStyles = makeStyles({
  button: {
    textAlign: 'left'
  }
});

const Workers: FunctionComponent<Props> = ({ data: { config, types, workers } }) => {
  const { currentTeamId } = useContext(TeamContext);
  const { setQuery } = useContext(QueryContext);

  const linkStyles = useLinkStyles();

  const [filterType, setFilterType] = useState<string>('__all__');

  const metrics = usePrometheus(config['grafana'], `avg(task_gpu_percent{vc_name="${currentTeamId}"}) by (instance)`);
  const workersGPUUtilization = useMemo(() => {
    const workersGPUUtilization: { [workerName: string]: number } = Object.create(null);
    if (metrics) {
      for (const { metric, value } of metrics.result) {
        const instanceIP = metric.instance.split(':', 1)[0];
        workersGPUUtilization[instanceIP] = value[1];
      }
    }
    return workersGPUUtilization;
  }, [metrics]);

  const data = useMemo(() => {
    let workersData = map(workers, (worker, id) => ({ id, ...worker }));
    if (filterType !== '__all__') {
      workersData = filter(workersData, ({ type }) => type === filterType);
    }
    each(workersData, (workerData) => {
      workerData.status = mapValues(workerData.status, (value) => {
        return {
          ...value,
          unschedulable: (value.total || 0) - (value.allocatable || 0),
          available: (value.allocatable || 0) - (value.used || 0)
        }
      });
      workerData.gpuUtilization = workersGPUUtilization[workerData.ip];
    })
    return workersData
  }, [workers, workersGPUUtilization, filterType]);
  const tableData = useTableData(data, { isTreeExpanded: true });

  const handleWorkerClick = useCallback((workerName: string) => () => {
    setQuery(workerName);
  }, [setQuery]);

  const resourceKinds = useRef<ResourceKind[]>(
    ['total', 'unschedulable', 'used', 'preemptable', 'available']
  ).current;
  const resourceColumns = useResourceColumns(resourceKinds);
  const columns = useMemo(() => {
    const columns: Column<any>[] = [{
      field: 'id',
      render: ({ id, ip, healthy }) => {
        if (typeof healthy === 'boolean') {
          return (
            <>
              <Tooltip title={`Show Pods on ${id}`}>
                <Link
                  component="button"
                  variant="subtitle2"
                  classes={linkStyles}
                  color={healthy ? 'inherit' : 'error'}
                  onClick={handleWorkerClick(id)}
                >
                  {id}
                </Link>
              </Tooltip>
              <Typography variant="caption">
                {ip}
              </Typography>
            </>
          );
        } else {
          return <Typography variant="subtitle2">{id}</Typography>;
        }
      }
    }];
    columns.push(...resourceColumns);
    columns.push({
      title: 'GPU Utilization',
      field: 'gpuUtilization',
      type: 'numeric',
      render: ({ gpuUtilization }) => gpuUtilization && <>{Number(gpuUtilization).toFixed(2)}%</>
    });
    return columns;
  }, [resourceColumns, handleWorkerClick, linkStyles]);

  const options = useRef<Options>({
    padding: 'dense',
    draggable: false,
    paging: false,
    detailPanelType: 'single'
  }).current;

  const handleSelectChange = useCallback((event: ChangeEvent<{ value: unknown }>) => {
    setFilterType(event.target.value as string);
  }, []);

  const detailPanel = useMemo<DetailPanel<any>[]>(() => {
    return [{
      tooltip: 'View Metrics',
      render: ({ ip }) => (
        <Card>
          <CardMedia
            component="iframe"
            src={`${config['grafana']}/dashboard/db/node-status?orgId=1&var-node=${ip}`}
            height="384"
            frameBorder="0"
          />
        </Card>
      )
    }];
  }, [config]);

  return (
    <SvgIconsMaterialTable
      title={(
        <>
          Show Type: <Select value={filterType} onChange={handleSelectChange}>
            <MenuItem value="__all__">All</MenuItem>
            {map(types, (type, name) => (
              <MenuItem key={name} value={name}>{name}</MenuItem>
            ))}
          </Select>
        </>
      )}
      data={tableData}
      columns={columns}
      options={options}
      detailPanel={detailPanel}
    />
  );
};

export default Workers;
