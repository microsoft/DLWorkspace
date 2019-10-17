import React, { useEffect, useState } from "react";
import useFetch from "use-http";
import TeamContext from "../../contexts/Teams";
import { useTimeoutFn  } from 'react-use';

type Jobs = object;
type UseJob = [Jobs | undefined, Error | undefined];
const useJobs = (): UseJob => {
  const { selectedTeam } = React.useContext(TeamContext);
  const [jobs, setJobs] = useState<Jobs>();
  const { data, error, get } = useFetch<Jobs>('/api');
  const params = new URLSearchParams({
    limit:'20'
  });
  const [isReady, reset, cancel] = useTimeoutFn(() => {
    get(`/teams/${selectedTeam}/jobs?${params}`);
  }, 3000);
  useEffect(() => {
    if (data == null) return;
    setJobs(data);
    if (isReady()) {
      reset();
    }
    return () => {
      cancel()
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
