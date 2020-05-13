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
import {
  AccountBox
} from '@material-ui/icons';
import {
  Column,
  Options
} from 'material-table';

import SvgIconsMaterialTable from '../../components/SvgIconsMaterialTable';
import TeamContext from '../../contexts/Team';
import usePrometheus from '../../hooks/usePrometheus';
import useTableData from '../../hooks/useTableData';
import { formatBytes, formatPercent, formatHours } from '../../utils/formats';

import QueryContext from './QueryContext';

const humanHours = (seconds: number) => {
  if (typeof seconds !== 'number') return seconds;
  return formatHours(seconds);
}

interface Props {
  data: any;
}

const Users: FunctionComponent<Props> = ({ data: { config, users } }) => {
  const { currentTeamId } = useContext(TeamContext);
  const { setQuery } = useContext(QueryContext);

  const [filterCurrent, setFilterCurrent] = useState(true);

  const gpuIdleMetrics = usePrometheus(config.grafana, `count (task_gpu_percent{vc_name="${currentTeamId}"} == 0) by (username)`);

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

    const totalStatus = Object.create(null);
    const total = {
      status: totalStatus,
      gpu: { booked: 0, idle: 0 },
      gpuIdle: 0,
      tableData: { isTreeExpanded: true }
    };
    data.push(total);
    for (const [userName, {types, gpu}] of entries<any>(users)) {
      if (types == null && filterCurrent) continue;
      const userStatus = Object.create(null);
      const gpuIdle = usersGPUIdle[userName];
      data.push({ id: userName, status: userStatus, gpu, gpuIdle });
      total.gpu.booked += get(gpu, 'booked', 0);
      total.gpu.idle += get(gpu, 'idle', 0);
      total.gpuIdle += gpuIdle !== undefined ? gpuIdle : 0;
      for (const [typeName, status] of entries(types)) {
        data.push({ id: typeName, userName, status })
        for (const resourceType of ['cpu', 'gpu', 'memory']) {
          for (const resourceKind of ['used', 'preemptable']) {
            set(userStatus, [resourceType, resourceKind],
              get(userStatus, [resourceType, resourceKind], 0) +
              get(status, [resourceType, resourceKind], 0));
            set(totalStatus, [resourceType, resourceKind],
              get(totalStatus, [resourceType, resourceKind], 0) +
              get(status, [resourceType, resourceKind], 0));
          }
        }
      }
    }
    return data;
  }, [filterCurrent, users, usersGPUIdle]);
  const tableData = useTableData(data);

  const handleUserClick = useCallback((userName: string) => () => {
    setQuery(userName);
  }, [setQuery]);

  const columns = useRef<Column<any>[]>([{
    field: 'id',
    render: (row) =>
      row.id === undefined
      ? <Typography variant="subtitle2">(total)</Typography>
      : row.userName
      ? <Typography variant="subtitle2">{row.id}</Typography>
      : (
        <Tooltip title={`Show ${row.id}'s Pods`}>
          <Link
            component="button"
            variant="subtitle2"
            style={{ textAlign: 'left' }}
            onClick={handleUserClick(row.id)}
          >
            <AccountBox fontSize="inherit"/>
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
        {formatBytes(get(status, ['memory', 'used'], 0))}
        {`(${formatBytes(get(status, ['memory', 'preemptable'], 0))})`}
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
    render: (data) => <>{humanHours(get(data, 'gpu.booked'))}</>,
    width: 'auto'
  } as Column<any>, {
    title: 'Idle GPU Last 30 days',
    field: 'gpu.idle',
    type: 'numeric',
    render: (data) => <>{humanHours(get(data, 'gpu.idle'))}</>,
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

      const ratio = idle / booked;
      const percent = formatPercent(ratio, 1)
      if (ratio > .5) {
        return <Typography variant="inherit" color="error">{percent}</Typography>
      }

      return <>{percent}</>;
    },
    width: 'auto'
  } as Column<any>]).current;

  const options = useRef<Options>({
    padding: 'dense',
    draggable: false,
    paging: false
  }).current;

  const parentChildData = useCallback(({ id, userName }, rows: any[]) => {
    if (id !== undefined) {
      return find(rows, ({ id }) => userName === id);
    }
  }, []);

  return (
    <SvgIconsMaterialTable
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
