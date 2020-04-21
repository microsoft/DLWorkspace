import React, {
  FunctionComponent,
  createContext,
  useContext,
  useEffect
} from 'react';

import useFetch from 'use-http-2';

import { useSnackbar } from 'notistack';

import TeamsContext from '../../../contexts/Teams';

interface ClusterContextValue {
  id: string;
  status?: { [key: string]: any };
}

const ClusterContext = createContext<ClusterContextValue>({ id: '' });

interface ClusterProviderProps {
  id: string;
}

const ClusterProvider: FunctionComponent<ClusterProviderProps> = ({ id, children }) => {
  const { selectedTeam } = useContext(TeamsContext);
  const { enqueueSnackbar, closeSnackbar } = useSnackbar();

  const { data: status, loading, error, get } = useFetch(
    `/api/v2/teams/${selectedTeam}/clusters/${id}`,
    undefined,
    [id, selectedTeam]);

  useEffect(() => {
    if (loading) return;

    const timeout = setTimeout(get, 3000);
    return () => {
      clearTimeout(timeout);
    }
  }, [loading, get]);
  useEffect(() => {
    if (error) {
      const key = enqueueSnackbar(`Failed to fetch status of cluster ${id}`, {
        variant: "error",
        persist: true
      });
      return () => {
        if (key != null) closeSnackbar(key);
      }
    }
  }, [error, id, enqueueSnackbar, closeSnackbar]);

  return React.createElement(ClusterContext.Provider, { value: { id, status } }, children);
}

const useCluster = () => useContext(ClusterContext);

export {
  ClusterProvider,
  useCluster,
};
