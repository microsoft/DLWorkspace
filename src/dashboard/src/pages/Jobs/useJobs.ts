import React, { useEffect, useState } from "react";
import { useGet } from "use-http";
import TeamContext from "../../contexts/Teams";

type Jobs = object;
type UseJob = [Jobs | undefined, Error | undefined];
const useJobs = (): UseJob => {
  const { selectedTeam } = React.useContext(TeamContext);
  const [jobs, setJobs] = useState<Jobs>();
  const { data, error, get } = useGet<Jobs>('/api');
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
    }
  }, [data, selectedTeam]);

  useEffect(() => {
    setJobs(undefined);
    get(`/teams/${selectedTeam}/jobs?${params}`);
  }, [selectedTeam]);

  if (jobs !== undefined) {
    return [jobs, undefined];
  }

  return [undefined, error];
}

export default useJobs;
