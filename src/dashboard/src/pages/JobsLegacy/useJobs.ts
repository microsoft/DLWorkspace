import * as React from 'react';
import { useEffect, useState } from "react";
import useFetch from "use-http";
import TeamContext from "../../contexts/Team";

type Jobs = object;
type UseJob = [Jobs | undefined, Error | undefined];
const useJobs = (): UseJob => {
  const { currentTeamId } = React.useContext(TeamContext);
  const [jobs, setJobs] = useState<Jobs>();
  const resp = useFetch<Jobs>('/api');
  const { data, error, get } = resp;
  const params = new URLSearchParams({
    limit:'20'
  });
  useEffect(() => {
    if (data == null) return;
    setJobs(data);
    const timeout = setTimeout(() => {
      get(`/teams/${currentTeamId}/jobs?${params}`);
    }, 3000);
    return () => {
      clearTimeout(timeout);
      setJobs([]);
      resp.abort()
    }
  }, [data, currentTeamId]);

  useEffect(() => {
    setJobs(undefined);
    get(`/teams/${currentTeamId}/jobs?${params}`);
    return () => {
      setJobs([]);
      resp.abort();
    }
  }, [currentTeamId]);

  if (jobs !== undefined) {
    return [jobs, undefined];
  }

  return [undefined, error];
}

export default useJobs;
