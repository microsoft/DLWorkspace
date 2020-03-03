import React, {
  FunctionComponent,
  useContext,
  useEffect
} from 'react';

import { get, values } from 'lodash';

import { Link as RouterLink } from 'react-router-dom';
import {
  Container,
  Link as UILink,
  Tooltip
} from '@material-ui/core';
import MaterialTable, {
  Column,
  Options
} from 'material-table';

import { useSnackbar } from 'notistack';
import useFetch from 'use-http-2';

import TeamsContext from '../../contexts/Teams';
import ClustersContext from '../../contexts/Clusters';
import useConstant from '../../hooks/useConstant';

const sumFields = (object: object, fieldPath: string | string[]) => {
  return values(object)
    .map(value => get(value, fieldPath, 0))
    .reduce((a, b) => a + b);
}

const humanBytes = (bytes: number) => {
  if (bytes >= 1024 * 1024 * 1024 * 1024) {
    return (bytes / 1024 / 1024 / 1024 / 1024).toFixed(1) + ' TiB'
  }
  if (bytes >= 1024 * 1024 * 1024) {
    return (bytes / 1024 / 1024 / 1024).toFixed(1) + ' GiB'
  }
  if (bytes >= 1024 * 1024) {
    return (bytes / 1024 / 1024).toFixed(1) + ' MiB'
  }
  if (bytes >= 1024) {
    return (bytes / 1024).toFixed(1) + ' KiB'
  }
  return bytes + ' B'
}

const getNumericColumn = (title: string, fieldPath: string | string[], bytes=false): Column<any> => ({
  title,
  type: 'numeric',
  searchable: false,
  render(cluster) {
    if (!cluster.status) return null;

    const value = sumFields(cluster.status.types, fieldPath)
    return <>{bytes ? humanBytes(value) : value}</>
  },
  customSort(clusterA, clusterB) {
    return sumFields(clusterA.status.types, fieldPath)
      - sumFields(clusterB.status.types, fieldPath)
  },
  cellStyle: {
    whiteSpace: 'nowrap'
  },
  // eslint-disable-next-line @typescript-eslint/ban-ts-ignore
  // @ts-ignore
  width: 130
});

const useClusterStatus = ({ id: clusterId }: { id: string }) => {
  const { selectedTeam } = useContext(TeamsContext);
  const { enqueueSnackbar, closeSnackbar } = useSnackbar();

  const { data, loading, error, get } = useFetch(
    `/api/v2/clusters/${clusterId}/teams/${selectedTeam}`,
    undefined,
    [clusterId, selectedTeam]);

  useEffect(() => {
    if (loading) return;

    const timeout = setTimeout(get, 3000);
    return () => {
      clearTimeout(timeout);
    }
  }, [loading, get]);
  useEffect(() => {
    if (error) {
      const key = enqueueSnackbar(`Failed to fetch status of cluster ${clusterId}`, {
        variant: "error",
        persist: true
      });
      return () => {
        if (key != null) closeSnackbar(key);
      }
    }
  }, [error, clusterId, enqueueSnackbar, closeSnackbar]);

  return { id: clusterId, tableData: { width: 'auto' }, status: data };
};

const Clusters: FunctionComponent = () => {
  const { clusters } = useContext(ClustersContext);

  const clustersStatus = clusters.map(useClusterStatus);

  const columns = useConstant<Column<any>[]>([{
    field: 'id',
    headerStyle: { width: 'auto' },
    render(cluster) {
      return (
        <UILink
          variant="subtitle2"
          component={RouterLink}
          to={cluster['id']}
        >
          {cluster['id']}
        </UILink>
      );
    },
    // eslint-disable-next-line @typescript-eslint/ban-ts-ignore
    // @ts-ignore
    width: 200
  },
  getNumericColumn('Total CPU', ['cpu', 'total']),
  getNumericColumn('Unschedulable CPU', ['cpu', 'unschedulable']),
  getNumericColumn('Used CPU', ['cpu', 'used']),
  getNumericColumn('Preempable CPU', ['cpu', 'preempable']),
  getNumericColumn('Available CPU', ['cpu', 'available']),
  getNumericColumn('Total GPU', ['gpu', 'total']),
  getNumericColumn('Unschedulable GPU', ['gpu', 'unschedulable']),
  getNumericColumn('Used GPU', ['gpu', 'used']),
  getNumericColumn('Preempable GPU', ['gpu', 'preempable']),
  getNumericColumn('Available GPU', ['gpu', 'available']),
  getNumericColumn('Total Memory', ['memory', 'total'], true),
  getNumericColumn('Unschedulable Memory', ['memory', 'unschedulable'], true),
  getNumericColumn('Used Memory', ['memory', 'used'], true),
  getNumericColumn('Preempable Memory', ['memory', 'preempable'], true),
  getNumericColumn('Available Memory', ['memory', 'available'], true),
  {
    title: 'Running Jobs',
    type: 'numeric' as 'numeric',
    field: 'status.runningJobs',
    render(cluster) {
      if (!cluster.status) return null;

      return (
        <Tooltip title={`View jobs in ${cluster.id}`}>
          <UILink variant="subtitle2" component={RouterLink} to={`/jobs-v2/${cluster.id}`}>
            {get(cluster, 'status.runningJobs', 0)}
          </UILink>
        </Tooltip>
      );
    },
    // eslint-disable-next-line @typescript-eslint/ban-ts-ignore
    // @ts-ignore
    width: 200
  }]);
  const options = useConstant<Options>({
    padding: "dense",
    fixedColumns: { left: 1, right: 1 },
    pageSize: 10,
  });

  return (
    <Container>
      <MaterialTable
        title="Clusters"
        data={clustersStatus}
        columns={columns}
        options={options}
      />
    </Container>
  )
}

export default Clusters;
