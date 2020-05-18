import * as React from 'react';
import {
  FunctionComponent,
  createContext,
  useCallback,
  useEffect,
  useState
} from 'react';
import useFetch from "use-http-2";

import { find } from "lodash";

interface TeamContext {
  teams?: any[];
  currentTeamId: string;
  setCurrentTeamId(teamId: string): void;
  clearCurrentTeamId(): void;
}

const TeamContext = createContext<TeamContext>({
  currentTeamId: '',
  setCurrentTeamId (teamId: string) { return; },
  clearCurrentTeamId () { return; }
});

const Provider: FunctionComponent = ({ children }) => {
  const { data: teams } = useFetch<any[]>('/api/teams', []);
  const [currentTeamId, setCurrentTeamId] = useState<string>(
    () => (window.localStorage.getItem('currentTeamId') || ''));
  const clearCurrentTeamId = useCallback(() => {
    window.localStorage.removeItem('currentTeamId');
  }, []);

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
      value={{ teams, currentTeamId, setCurrentTeamId, clearCurrentTeamId }}
      children={children}
    />
  );
}

export default TeamContext;
export { Provider };
