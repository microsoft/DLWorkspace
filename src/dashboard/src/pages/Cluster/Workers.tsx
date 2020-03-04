import React, {
  FunctionComponent,
  useCallback,
  useMemo,
  useRef
} from 'react';
import {
  Link as RouterLink
} from 'react-router-dom';
import {
  each,
  find,
  keys,
  map,
  mapValues
} from 'lodash';
import {
  Link as UILink,
  Typography
} from '@material-ui/core';
import {
  Favorite
} from '@material-ui/icons';
import MaterialTable, {
  Column,
  Options
} from 'material-table';

import useTableData from '../../hooks/useTableData';

import useResourceColumns, { ResourceKind } from '../Clusters/useResourceColumns';

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
        if (typeof healthy === 'boolean') {
          return (
            <UILink variant="subtitle2" component={RouterLink} to={`./${id}`}>
              { healthy || <Favorite color="error" fontSize="inherit"/> }
              {id}
            </UILink>
          );
        } else {
          return <Typography variant="subtitle2">{id}</Typography>;
        }
      }
    }];
    columns.push(...resourceColumns);
    columns.push({
      title: 'Pods',
      type: 'numeric',
      render: ({ ip, pods }) => ip ?  <>{keys(pods).length}</> : null
    });
    return columns;
  }, [resourceColumns]);

  const options = useRef<Options>({
    padding: 'dense',
    toolbar: false,
    draggable: false,
    paging: false,
    detailPanelColumnAlignment: 'right'
  }).current;

  const parentChildData = useCallback(({ type }, rows: any[]) => {
    return find(rows, ({ id }) => type === id);
  }, []);

  return (
    <MaterialTable
      data={tableData}
      columns={columns}
      options={options}
      parentChildData={parentChildData}
    />
  );
};

export default Workers;
