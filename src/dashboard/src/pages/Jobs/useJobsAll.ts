import React, { useEffect, useState } from "react";
import useFetch from "use-http";
import TeamContext from "../../contexts/Teams";
type Jobs = object;
type useJobsAll = [Jobs | undefined, Error | undefined];

const useJobsAll = (openKillWarn?: boolean,openApproveWan?: boolean): useJobsAll => {
  const [jobsAll, setJobsAll] = useState<Jobs>();
  const { selectedTeam } = React.useContext(TeamContext);
  const params = new URLSearchParams({
    user:'all',
    limit:'100'
  });
  const resp = useFetch<Jobs>('/api');
  const { data, error, get } = resp;

  useEffect(() => {
    if (data == null) return;
    setJobsAll(data);

    const timeout = setTimeout(() => {
      get(`/teams/${selectedTeam}/jobs?${params}`);
    }, 3000);
    return () => {
      clearTimeout(timeout);
      setJobsAll([])
      resp.abort()
    }
  }, [data]);

  useEffect(() => {
    setJobsAll(undefined);
    get(`/teams/${selectedTeam}/jobs?${params}`);
    return () => {
      setJobsAll([])
      resp.abort()
    }
  }, [selectedTeam]);


  if (jobsAll !== undefined) {
    return [jobsAll, undefined];
  }

  return [undefined, error];
}

export default useJobsAll;
