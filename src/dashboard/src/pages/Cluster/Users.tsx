import React, {
  FunctionComponent,
  useCallback,
  useMemo,
  useRef,
  useState
} from 'react';
import { entries, find, get, set } from 'lodash';

import {
  Button,
  ButtonGroup,
  Typography
} from '@material-ui/core';
import MaterialTable, {
  Column,
  Options
} from 'material-table';

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

const Users: FunctionComponent<{ users: any }> = ({ users }) => {
  const [filterCurrent, setFilterCurrent] = useState(true);

  const handleAllClick = useCallback(() => setFilterCurrent(false), [setFilterCurrent]);
  const handleCurrentClick = useCallback(() => setFilterCurrent(true), [setFilterCurrent]);

  const data = useMemo(() => {
    const data = [];
    const total = { id: 'Total' };
    for (const [userName, {types, gpu}] of entries<any>(users)) {
      if (types == null && filterCurrent) continue;
      const userStatus = Object.create(null)
      data.push({ id: userName, status: userStatus, gpu });
      for (const [typeName, status] of entries(types)) {
        data.push({ id: typeName, userName, status })
        for (const resourceType of ['cpu', 'gpu', 'memory']) {
          for (const resourceKind of ['used', 'preempable']) {
            set(userStatus, [resourceType, resourceKind],
              get(userStatus, [resourceType, resourceKind], 0) +
              get(status, [resourceType, resourceKind], 0))
            set(total, ['status', resourceType, resourceKind],
              get(total, ['status', resourceType, resourceKind], 0) +
              get(status, [resourceType, resourceKind], 0))
          }
        }
      }
      set(total, ['gpu', 'booked'],
        get(total, ['gpu', 'booked'], 0) +
        get(gpu, ['booked'], 0));
      set(total, ['gpu', 'idle'],
        get(total, ['gpu', 'idle'], 0) +
        get(gpu, ['idle'], 0));
    }
    data.push(total);
    return data;
  }, [filterCurrent, users]);
  const tableData = useTableData(data);

  const columns = useRef<Column<any>[]>([{
    field: 'id',
    render: (row) => row.userName
      ? <Typography variant="subtitle2">{row.id}</Typography>
      : <Typography variant="subtitle1">{row.id}</Typography>
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
    title: 'Idle GPU'
  }, {
    title: 'Booked GPU Last Month',
    field: 'gpu.booked',
    type: 'numeric',
    render: (data) => <>{humanSeconds(get(data, 'gpu.booked'))}</>,
    width: 'auto'
  } as Column<any>, {
    title: 'Idle GPU Last Month',
    field: 'gpu.idle',
    type: 'numeric',
    render: (data) => <>{humanSeconds(get(data, 'gpu.idle'))}</>,
    width: 'auto'
  } as Column<any>, {
    title: 'Idle GPU % Last Month',
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
        <ButtonGroup size="small">
          <Button disabled={!filterCurrent} onClick={handleAllClick}>All Users</Button>
          <Button disabled={filterCurrent} onClick={handleCurrentClick}>Current Users</Button>
        </ButtonGroup>
      }
      data={tableData}
      columns={columns}
      options={options}
      parentChildData={parentChildData}
    />
  )
};

export default Users;
