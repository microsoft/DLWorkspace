import React, {
  FunctionComponent,
  useCallback,
  useMemo,
  useRef
} from 'react';
import {
  Link as RouterLink,
  useParams
} from 'react-router-dom';
import {
  each,
  find,
  map,
  mapValues
} from 'lodash';
import {
  Box,
  Link as UILink,
  Typography
} from '@material-ui/core';
import {
  LibraryBooks
} from '@material-ui/icons';
import MaterialTable, {
  Column,
  DetailPanel,
  Options
} from 'material-table';

import useTableData from '../../hooks/useTableData';

import useResourceColumns, { ResourceKind, humanBytes } from '../Clusters/useResourceColumns';

const Pods: FunctionComponent<{ pods: any }> = ({ pods }) => {
  const { clusterId } = useParams();
  const data = useMemo(() => {
    return map(pods, (pod, name) => ({ name, ...pod }));
  }, [pods]);
  const tableData = useTableData(data);

  const columns = useRef<Column<any>[]>([{
    field: 'name',
    width: 'auto',
    render: ({ name, jobId }) => (
      <UILink
        variant="subtitle2"
        component={RouterLink}
        to={`/jobs-v2/${clusterId}/${jobId}`}
      >
        {name}
      </UILink>
    )
  } as Column<any>, {
    title: 'Team',
    field: 'team',
    width: 'auto'
  } as Column<any>, {
    title: 'User',
    field: 'user',
    width: 'auto'
  } as Column<any>, {
    title: 'CPU',
    type: 'numeric',
    field: 'cpu',
    width: 'auto'
  } as Column<any>, {
    title: 'GPU',
    type: 'numeric',
    field: 'gpu',
    width: 'auto'
  } as Column<any>, {
    title: 'Memory',
    type: 'numeric',
    field: 'memory',
    render: ({ memory }) => <>{humanBytes(memory)}</>,
    width: 'auto'
  } as Column<any>]).current;

  const options = useRef<Options>({
    toolbar: false,
    padding: 'dense',
    draggable: false,
    paging: false
  }).current;
  return (
    <Box p={4}>
      <MaterialTable
        data={tableData}
        columns={columns}
        options={options}
      />
    </Box>
  );
}

interface Props {
  types: any;
  workers: any;
}

const Workers: FunctionComponent<Props> = ({ types, workers }) => {
  const data = useMemo(() => {
    const typesData = map(types, (status, id) => ({ id, status }));
    const workersData = map(workers, (worker, id) => ({ id, ...worker }));
    each(workersData, (workerData) => {
      workerData.status = mapValues(workerData.status, (value) => {
        return {
          ...value,
          unschedulable: (value.total || 0) - (value.allocatable || 0),
          available: (value.allocatable || 0) - (value.used || 0)
        }
      });
    })
    return typesData.concat(workersData)
  }, [types, workers]);
  const tableData = useTableData(data, { isTreeExpanded: true });

  const resourceKinds = useRef<ResourceKind[]>(
    ['total', 'unschedulable', 'used', 'preemptable', 'available']
  ).current;
  const resourceColumns = useResourceColumns(resourceKinds);
  const columns = useMemo(() => {
    const columns: Column<any>[] = [{
      field: 'id',
      render: ({ id, healthy }) => {
        if (healthy === true) {
          return <Typography variant="subtitle2">{id}</Typography>;
        } else if (healthy === false) {
          return <Typography variant="subtitle2" color="error">{id}</Typography>;
        } else {
          return <Typography variant="subtitle1">{id}</Typography>;
        }
      }
    }];
    columns.push(...resourceColumns);
    return columns;
  }, [resourceColumns]);

  const options = useRef<Options>({
    padding: 'dense',
    toolbar: false,
    draggable: false,
    paging: false,
    detailPanelColumnAlignment: 'right'
  }).current;

  const detailPanel = useCallback(({ pods }: any): DetailPanel<any> => {
    if (!pods) {
      return {
        icon: ' ',
        disabled: true,
        render: () => <div/>
      };
    }
    return {
      icon: LibraryBooks,
      tooltip: 'Pods',
      render: () => <Pods pods={pods}/>
    };
  }, []);

  const parentChildData = useCallback(({ type }, rows: any[]) => {
    return find(rows, ({ id }) => type === id);
  }, []);

  return (
    <MaterialTable
      data={tableData}
      columns={columns}
      options={options}
      detailPanel={[detailPanel]}
      parentChildData={parentChildData}
    />
  );
};

export default Workers;
