import * as React from 'react';
import {
  FunctionComponent,
  useCallback,
  useEffect,
  useMemo,
  useRef,
} from 'react';

import { each, mapValues, sortBy } from 'lodash';

import { Helmet } from 'react-helmet';
import { useParams } from 'react-router';

import {
  Button,
  Container,
  Typography,
} from '@material-ui/core';

import { Column, Options } from 'material-table';
import { useSnackbar } from 'notistack';

import useFetch from 'use-http-1';

import SvgIconMaterialTable from '../../components/SvgIconsMaterialTable';

const useQuota = (clusterId: string) => {
  const { enqueueSnackbar, closeSnackbar } = useSnackbar();
  const { response, error, get } = useFetch(`/api/clusters/${clusterId}/quota`, [clusterId]);

  useEffect(() => {
    if (error !== undefined) {
      const key = enqueueSnackbar(`Failed to fetch quota data: ${error.message}`, {
        variant: 'error',
        persist: true,
        action: <Button color="inherit" onClick={() => get()}>Retry</Button>,
      })
      if (key != null) {
        return () => closeSnackbar(key);
      }
    }
  }, [error, enqueueSnackbar, get, closeSnackbar]);

  return { data: response.ok ? response.data : undefined, get };
};

const useConfig = (clusterId: string) => {
  const { enqueueSnackbar, closeSnackbar } = useSnackbar();
  const { response, error, get } = useFetch(`/api/clusters/${clusterId}`, [clusterId]);

  useEffect(() => {
    if (error !== undefined) {
      const key = enqueueSnackbar(`Failed to fetch cluster config: ${error.message}`, {
        variant: 'error',
        persist: true,
        action: <Button color="inherit" onClick={() => get()}>Retry</Button>,
      })
      if (key != null) {
        return () => closeSnackbar(key);
      }
    }
  }, [error, enqueueSnackbar, get, closeSnackbar]);

  return response.ok ? response.data : undefined;
}

type QuotaRowData = {
  id: string;
  types: { [type: string]: number };
}

const Quota: FunctionComponent = () => {
  const { clusterId } = useParams<{ clusterId: string }>();
  const { enqueueSnackbar } = useSnackbar();
  const config = useConfig(clusterId);
  const { data: quota, get: getQuota } = useQuota(clusterId);
  const { response, patch } = useFetch(`/api/clusters/${clusterId}/quota`, {
    headers: { 'Content-Type': 'application/json' }
  });

  const isPureCPU = useMemo(() => {
    if (config == null) return undefined;
    return Boolean(config.isPureCPU);
  }, [config]);

  const idColumn = useRef<Column<QuotaRowData>>({
    field: 'id',
    editable: 'never',
    render: ({ id }) => (
      <Typography variant="subtitle2">
        {id}
      </Typography>
    ),
  }).current;

  const [data, columns] = useMemo(() => {
    if (quota === undefined || isPureCPU === undefined) {
      return [[], [idColumn]];
    }
    const data: QuotaRowData[] = [];
    const columns = [idColumn];
    const typeNameSet: { [typeName: string]: true } = Object.create(null);
    each(quota, ({ resourceQuota: quota }, id) => {
      const types = isPureCPU ? quota.cpu : quota.gpu;
      data.push({ id, types });
      each(types, (_, typeName) => {
        typeNameSet[typeName] = true;
      });
    });
    each(typeNameSet, (_, typeName) => {
      columns.push({
        field: 'types.' + typeName,
        type: 'numeric',
        title: typeName
      })
    })
    return [sortBy(data, 'id'), columns];
  }, [quota, isPureCPU, idColumn]);

  const options = useRef<Options>({
    actionsColumnIndex: -1,
    search: false,
    paging: false,
  }).current;

  const title = useMemo(() => {
    if (isPureCPU === undefined) {
      return `Quota of ${clusterId}`
    } else if (isPureCPU) {
      return `CPU Quota of ${clusterId}`
    } else {
      return `GPU Quota of ${clusterId}`
    }
  }, [isPureCPU, clusterId]);

  const isEditable = useCallback(() => true, []);
  const handleRowUpdate = useCallback((data: QuotaRowData) => {
    const body = {
      [data.id]: {
        resourceQuota: {
          [isPureCPU ? 'cpu' : 'gpu']: mapValues(data.types, Number),
        },
      },
    };
    return patch(body).then(() => {
      if (!response.ok) {
        throw Error(response.data);
      } else {
        return getQuota();
      }
    }).catch((error) => {
      enqueueSnackbar(`Failed to update quota: ${error.message}`, {
        variant: 'error'
      });
      throw error;
    })
  }, [isPureCPU, patch, response, getQuota, enqueueSnackbar]);

  return (
    <Container>
      <Helmet title={title}/>
      <SvgIconMaterialTable
        title={title}
        isLoading={config === undefined || quota === undefined}
        data={data}
        columns={columns}
        editable={{ isEditable, onRowUpdate: handleRowUpdate }}
        options={options}
      />
    </Container>
  );
};

export default Quota;
