import React, {
  FunctionComponent,
  useMemo,
  useRef
} from 'react';
import { Link as RouterLink } from 'react-router-dom';

import { map } from 'lodash';

import {
  Link as UILink,
  Tooltip
} from '@material-ui/core';
import MaterialTable, {
  Column,
  Options
} from 'material-table';

import { humanBytes } from '../Clusters/useResourceColumns';

import useTableData from '../../hooks/useTableData';
import useRouteParams from './useRouteParams';

const Pods: FunctionComponent<{ data: any }> = ({ data }) => {
  const { clusterId } = useRouteParams();
  const pods = useMemo(() => {
    return map(data.pods, (pod, id) => ({ id, ...pod }));
  }, [data]);
  const tableData = useTableData(pods);

  const columns = useRef<Column<any>[]>([{
    field: 'id',
    render: ({ id, jobId }) => (
      <Tooltip title={`See Job ${jobId}`}>
        <UILink variant="subtitle2" component={RouterLink} to={`/jobs-v2/${clusterId}/${jobId}`}>
          {id}
        </UILink>
      </Tooltip>
    ),
    width: 'auto'
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
    field: 'cpu',
    type: 'numeric',
    width: 'auto'
  } as Column<any>, {
    title: 'GPU',
    field: 'gpu',
    type: 'numeric',
    width: 'auto'
  } as Column<any>, {
    title: 'Memory',
    field: 'memoty',
    type: 'numeric',
    render: ({ memory }) => <>{humanBytes(memory)}</>,
    width: 'auto'
  } as Column<any>]).current;
  const options = useRef<Options>({
    toolbar: false,
    paging: false,
  }).current;

  return (
    <MaterialTable
      data={tableData}
      columns={columns}
      options={options}
    />
  );
};

export default Pods;
