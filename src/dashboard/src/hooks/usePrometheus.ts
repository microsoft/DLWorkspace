import {
  useEffect,
  useMemo,
} from 'react';
import useFetch from 'use-http-1';

const usePrometheus = (grafana: string | undefined, query: string) => {
  const url = useMemo(() => {
    if (grafana === undefined) return;
    const encodedQuery = encodeURIComponent(query);
    return `${grafana}/api/datasources/proxy/1/api/v1/query?query=${encodedQuery}`;
  }, [grafana, query]);

  const { data, loading, get, abort } = useFetch(url);

  const result = useMemo(() => {
    if (data === undefined) return;
    if (data.status !== 'success') return;
    return data.data;
  }, [data]);

  useEffect(() => {
    if (url !== undefined) {
      get();
      return abort;
    }
  }, [url, get, abort]);

  useEffect(() => {
    if (loading) return;
    const timeout = setTimeout(get, 3000);
    return () => { clearTimeout(timeout); }
  }, [loading, get]);

  return result;
};

export default usePrometheus;
