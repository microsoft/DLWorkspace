import React, {
  FunctionComponent,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  useMemo
} from 'react';

import { entries, find, identity, get, set } from 'lodash';

import { Link as RouterLink } from 'react-router-dom';
import {
  Container,
  Link as UILink,
  TableSortLabel,
  Tooltip,
  Typography,
  useTheme
} from '@material-ui/core';
import {
  More
} from '@material-ui/icons';
import MaterialTable, {
  Column,
  Options
} from 'material-table';

import { useSnackbar } from 'notistack';
import useFetch from 'use-http-2';

import TeamsContext from '../../contexts/Teams';
import ClustersContext from '../../contexts/Clusters';
import useTableData from '../../hooks/useTableData';

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

  return useMemo(() => ({ id: clusterId, status: data }), [clusterId, data]);
};

const Clusters: FunctionComponent = () => {
  const { clusters } = useContext(ClustersContext);
  const theme = useTheme();

  type ResourceType = 'cpu' | 'gpu' | 'memory';
  const [expandedResourceType, setExpandedResourceType] = useState<ResourceType>('gpu');

  const clustersStatus = clusters.map(useClusterStatus);

  const clusterTypesStatus = useMemo(() => {
    const clusterTypesStatus = [];
    for (const { id: clusterId, status: clusterStatus } of clustersStatus) {
      if (clusterStatus == null) {
        clusterTypesStatus.push({ id: clusterId })
        continue;
      }

      const clusterSumStatus = Object.create(null)
      clusterTypesStatus.push({
        id: clusterId,
        status: clusterSumStatus,
        runningJobs: clusterStatus.runningJobs
      })

      for (const [typeId, typeStatus] of entries(clusterStatus.types)) {
        clusterTypesStatus.push({
          id: typeId,
          clusterId,
          status: typeStatus
        })

        for (const type of ['cpu', 'gpu', 'memory']) {
          for (const kind of ['total', 'unschedulable', 'used', 'preempable', 'available']) {
            const path = [type, kind]
            set(clusterSumStatus, path, get(clusterSumStatus, path, 0) + get(typeStatus, path, 0));
          }
        }
      }
    }
    return clusterTypesStatus;
  }, clustersStatus); // eslint-disable-line react-hooks/exhaustive-deps

  const data = useTableData(clusterTypesStatus);
  const typeColor = useMemo(() => ({
    cpu: theme.palette.background.default, // blue[50],
    gpu: theme.palette.background.paper, // cyan[50],
    memory: theme.palette.background.default, // teal[50]
  }), [theme]);

  const columns = useMemo(() => {
    const columns: Array<Column<any>> = [];

    columns.push({
      field: 'id',
      render: (data) => data.clusterId == null
        ? <UILink variant="subtitle2" component={RouterLink} to={data.id}>{data.id}</UILink>
        : <Typography variant="subtitle2">{data.id}</Typography>,
      // eslint-disable-next-line @typescript-eslint/ban-ts-ignore
      // @ts-ignore: https://github.com/mbrn/material-table/pull/1659
      width: 'auto'
    });

    for (const title of ['CPU', 'GPU', 'Memory']) {
      const type = title.toLowerCase() as 'cpu' | 'gpu' | 'memory';
      const process = type === 'memory' ? humanBytes : identity;
      const style = { backgroundColor: typeColor[type] };
      columns.push({
        title: (
          <TableSortLabel
            active
            IconComponent={More}
            onClick={() => setExpandedResourceType(type)}
          >
            {title}
          </TableSortLabel>
        ),
        tooltip: 'Expand',
        hidden: expandedResourceType === type,
        headerStyle: { whiteSpace: 'nowrap', ...style },
        cellStyle: { whiteSpace: 'nowrap', ...style },
        render: ({ status }) => status && (
          <>
            {process(get(status, [type, 'available'], 0))}
            /
            {process(get(status, [type, 'total'], 0))}
          </>
        ),
        sorting: false,
        searchable: false,
        // eslint-disable-next-line @typescript-eslint/ban-ts-ignore
        // @ts-ignore: https://github.com/mbrn/material-table/pull/1659
        width: 'auto'
      });
      for (const adjective of ['Total', 'Unschedulable', 'Used', 'Preempable', 'Available']) {
        const kind = adjective.toLowerCase();
        columns.push({
          title: `${title} ${adjective}`,
          type: 'numeric',
          field: `status.${type}.${kind}`,
          hidden: expandedResourceType !== type,
          render: ({ status }) => status && (
            <>{process(get(status, [type, kind], 0))}</>
          ),
          headerStyle: style,
          cellStyle: style,
          // eslint-disable-next-line @typescript-eslint/ban-ts-ignore
          // @ts-ignore: https://github.com/mbrn/material-table/pull/1659
          width: 'auto'
        });
      }
    }

    columns.push({
      title: 'Running Jobs',
      type: 'numeric',
      field: 'runningJobs',
      render: (data: any) => data.clusterId == null ? (
        <Tooltip title={`View jobs in ${data.id}`}>
          <UILink variant="subtitle2" component={RouterLink} to={`/jobs-v2/${data.id}`}>
            {get(data, 'runningJobs', 0)}
          </UILink>
        </Tooltip>
      ) : null,
      // eslint-disable-next-line @typescript-eslint/ban-ts-ignore
      // @ts-ignore: https://github.com/mbrn/material-table/pull/1659
      width: 'auto'
    })

    return columns;
  }, [expandedResourceType, typeColor]);
  const options = useRef<Options>({
    padding: "dense",
    pageSize: 10,
    draggable: false
  }).current;
  const parentChildData = useCallback(({ clusterId }, rows: any[]) => {
    return find(rows, ({ id }) => clusterId === id);
  }, []);

  return (
    <Container>
      <MaterialTable
        title="Clusters"
        data={data}
        columns={columns}
        options={options}
        parentChildData={parentChildData}
      />
    </Container>
  )
}

export default Clusters;
