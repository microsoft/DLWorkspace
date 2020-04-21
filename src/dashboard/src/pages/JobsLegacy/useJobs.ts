import React, { useEffect, useState } from "react";
import useFetch from "use-http";
import TeamContext from "../../contexts/Teams";

type Jobs = object;
type UseJob = [Jobs | undefined, Error | undefined];
const useJobs = (): UseJob => {
  const { selectedTeam } = React.useContext(TeamContext);
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
      get(`/teams/${selectedTeam}/jobs?${params}`);
    }, 3000);
    return () => {
      clearTimeout(timeout);
      setJobs([]);
      resp.abort()
    }
  }, [data, selectedTeam]);

  useEffect(() => {
    setJobs(undefined);
    get(`/teams/${selectedTeam}/jobs?${params}`);
    return () => {
      setJobs([]);
      resp.abort();
    }
  }, [selectedTeam]);

  if (jobs !== undefined) {
    return [jobs, undefined];
  }

  return [undefined, error];
}

export default useJobs;
