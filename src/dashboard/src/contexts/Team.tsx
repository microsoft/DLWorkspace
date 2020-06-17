import * as React from 'react';
import {
  FunctionComponent,
  createContext,
  useContext,
  useEffect,
  useState
} from 'react';
import useFetch from "use-http-2";

import { find } from "lodash";

import UserContext from './User';

interface TeamContext {
  teams?: any[];
  currentTeamId: string;
  setCurrentTeamId(teamId: string): void;
}

const TeamContext = createContext<TeamContext>({
  currentTeamId: '',
  setCurrentTeamId (teamId: string) { return; },
});

const Provider: FunctionComponent = ({ children }) => {
  const { email } = useContext(UserContext);

  const [teams, setTeams] = useState<any[] | undefined>(() => {
    try {
      const teams = JSON.parse(window.localStorage.getItem('teams') || '')
      if (Array.isArray(teams)) {
        return teams;
      }
    } catch (e) { /* ignored */ }
  });
  const [currentTeamId, setCurrentTeamId] = useState<string>(
    () => (window.localStorage.getItem('currentTeamId') || ''));

  const { get } = useFetch<any[]>('/api/teams');

  useEffect(() => {
    if (email === undefined) { // Not signed in
      // Clean teams cache
      window.localStorage.removeItem('teams')
    }
  }, [email]);

  useEffect(() => {
    if (
      teams == null && // No cached team
      email !== undefined // Signed in
    ) {
      // Fetch teams from backend
      get().then((teams) => {
        if (teams.length > 0) {
          window.localStorage.setItem('teams', JSON.stringify(teams))
        }
        setTeams(teams)
      }, () => {
        setTeams([])
      })
    }
  }, [teams, email, get]);

  useEffect(() => {
    // Validate currentTeamId
    if (teams == null || teams.length === 0) return;
    const team = currentTeamId !== ''
      ? find(teams, ({ id }) => id === currentTeamId)
      : null;
    if (team == null) {
      setCurrentTeamId(teams[0].id);
    }
  }, [teams, currentTeamId]);

  useEffect(() => {
    // Persistent currentTeamId
    if (currentTeamId === '') return;
    window.localStorage.setItem('currentTeamId', currentTeamId);
  }, [currentTeamId]);

  return (
    <TeamContext.Provider
      value={{ teams, currentTeamId, setCurrentTeamId }}
      children={children}
    />
  );
}

export default TeamContext;
export { Provider };
