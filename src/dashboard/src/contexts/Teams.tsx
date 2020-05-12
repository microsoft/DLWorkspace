import React, { useEffect } from 'react';
import useFetch from "use-http";

import _ from "lodash";

interface Context {
  teams: any;
  selectedTeam: any;
  saveSelectedTeam(team: React.SetStateAction<string>): void;
}

const Context = React.createContext<Context>({
  teams: [],
  selectedTeam: '',
  saveSelectedTeam: function(team: React.SetStateAction<string>) {},
});

export default Context;
export const Provider: React.FC = ({ children }) => {
  const fetchTeamsUrl = '/api/teams';
  const { data: teams } = useFetch(fetchTeamsUrl, { onMount: true });
  const [selectedTeam, setSelectedTeam] = React.useState<string>('');
  const saveSelectedTeam = (team: React.SetStateAction<string>) => {
    setSelectedTeam(team);
    localStorage.setItem('team',team.toString())
    window.location.reload()
  };
  useEffect(()=> {
    if (localStorage.getItem('team')) {
      setSelectedTeam((String)(localStorage.getItem('team')))
    } else {
      setSelectedTeam(_.map(teams, 'id')[0]);
    }
  },[teams])
  return <Context.Provider value={{ teams, selectedTeam, saveSelectedTeam }} children={children}/>;
};
