import React, {
  FunctionComponent,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState
} from 'react';
import { entries, find, get, set } from 'lodash';

import {
  Button,
  Link,
  Tooltip,
  Typography
} from '@material-ui/core';
import MaterialTable, {
  Column,
  Options
} from 'material-table';

import TeamsContext from '../../contexts/Teams';
import usePrometheus from '../../hooks/usePrometheus';
import useTableData from '../../hooks/useTableData';
import { humanBytes } from '../Clusters/useResourceColumns';

const humanSeconds = (seconds: number) => {
  if (typeof seconds !== 'number') return seconds;
  if (seconds >= 60 * 60) {
    return (seconds / 60 / 60).toFixed(0) + ' hours'
  }
  if (seconds >= 60) {
    return (seconds / 60).toFixed(0) + ' minutes'
  }
  return seconds + ' s'
}

interface Props {
  clusterConfig: any;
  users: any;
  onSearchPods: (query: string) => void;
}

const Users: FunctionComponent<Props> = ({ clusterConfig, users, onSearchPods }) => {
  const { selectedTeam } = useContext(TeamsContext);

  const [filterCurrent, setFilterCurrent] = useState(true);

  const gpuIdleMetrics = usePrometheus(clusterConfig, `count (task_gpu_percent{vc_name="${selectedTeam}"} == 0) by (username)`);

  const handleButtonClick = useCallback(() => {
    setFilterCurrent((filterCurrent) => !filterCurrent);
  }, [setFilterCurrent]);

  const usersGPUIdle = useMemo(() => {
    const usersGPUIdle: { [user: string]: number } = Object.create(null);
    if (gpuIdleMetrics != null)  {
      for (const { metric, value } of gpuIdleMetrics.result) {
        usersGPUIdle[metric.username] = Number(value[1]);
      }
    }
    return usersGPUIdle;
  }, [gpuIdleMetrics]);

  const data = useMemo(() => {
    const data = [];
    for (const [userName, {types, gpu}] of entries<any>(users)) {
      if (types == null && filterCurrent) continue;
      const userStatus = Object.create(null);
      const gpuIdle = usersGPUIdle[userName];
      data.push({ id: userName, status: userStatus, gpu, gpuIdle });
      for (const [typeName, status] of entries(types)) {
        data.push({ id: typeName, userName, status })
        for (const resourceType of ['cpu', 'gpu', 'memory']) {
          for (const resourceKind of ['used', 'preemptable']) {
            set(userStatus, [resourceType, resourceKind],
              get(userStatus, [resourceType, resourceKind], 0) +
              get(status, [resourceType, resourceKind], 0));
          }
        }
      }
    }
    return data;
  }, [filterCurrent, users, usersGPUIdle]);
  const tableData = useTableData(data);

  const handleUserClick = useCallback((userName: string) => () => {
    onSearchPods(userName);
  }, [onSearchPods]);

  const columns = useRef<Column<any>[]>([{
    field: 'id',
    render: (row) => row.userName
      ? <Typography variant="subtitle2">{row.id}</Typography>
      : (
        <Tooltip title={`Show ${row.id}'s Pods`}>
          <Link
            component="button"
            variant="subtitle2"
            style={{ textAlign: 'left' }}
            onClick={handleUserClick(row.id)}
          >
            {row.id}
          </Link>
        </Tooltip>
      )
  }, {
    title: 'CPU',
    field: 'status.cpu.used',
    tooltip: 'Used (Preemptable)',
    render: ({ status }) => status && (
      <>
        {get(status, ['cpu', 'used'], 0)}
        {`(${get(status, ['cpu', 'preemptable'], 0)})`}
      </>
    ),
    searchable: false,
    width: 'auto'
  } as Column<any>, {
    title: 'GPU',
    field: 'status.gpu.used',
    tooltip: 'Used (Preemptable)',
    render: ({ status }) => status && (
      <>
        {get(status, ['gpu', 'used'], 0)}
        {`(${get(status, ['gpu', 'preemptable'], 0)})`}
      </>
    ),
    searchable: false,
    width: 'auto'
  } as Column<any>, {
    title: 'Memory',
    field: 'status.memory.used',
    tooltip: 'Used (Preemptable)',
    render: ({ status }) => status && (
      <>
        {humanBytes(get(status, ['memory', 'used'], 0))}
        {`(${humanBytes(get(status, ['memory', 'preemptable'], 0))})`}
      </>
    ),
    searchable: false,
    width: 'auto'
  } as Column<any>, {
    title: 'GPU Idle',
    field: 'gpuIdle',
    type: 'numeric',
    render: ({ gpuIdle }) => typeof gpuIdle === 'number' && (
      <Typography variant="inherit" color={gpuIdle > 0 ? "error" : "inherit"}>
        {gpuIdle}
      </Typography>
    ),
    width: 'auto'
  } as Column<any>, {
    title: 'Booked GPU Last 30 days',
    field: 'gpu.booked',
    type: 'numeric',
    render: (data) => <>{humanSeconds(get(data, 'gpu.booked'))}</>,
    width: 'auto'
  } as Column<any>, {
    title: 'Idle GPU Last 30 days',
    field: 'gpu.idle',
    type: 'numeric',
    render: (data) => <>{humanSeconds(get(data, 'gpu.idle'))}</>,
    width: 'auto'
  } as Column<any>, {
    title: 'Idle GPU % Last 30 days',
    field: 'gpu.idle',
    type: 'numeric',
    render: (data) => {
      if (data.userName) return;

      const booked = get(data, 'gpu.booked', 0);
      const idle = get(data, 'gpu.idle', 0);

      if (booked === 0) return <>N/A</>;

      const percent = (idle / booked) * 100;
      if (percent > 50) {
        return <Typography variant="inherit" color="error">{percent.toFixed(1)}%</Typography>
      }

      return <>{percent.toFixed(1)}%</>;
    },
    width: 'auto'
  } as Column<any>]).current;

  const options = useRef<Options>({
    padding: 'dense',
    draggable: false,
    paging: false
  }).current;

  const parentChildData = useCallback(({ userName }, rows: any[]) => {
    return find(rows, ({ id }) => userName === id);
  }, []);

  return (
    <MaterialTable
      title={
        <Button variant="outlined" onClick={handleButtonClick}>
          { filterCurrent ? "Show All Users" : "Show Current Users Only" }
        </Button>
      }
      data={tableData}
      columns={columns}
      options={options}
      parentChildData={parentChildData}
    />
  )
};

export default Users;
