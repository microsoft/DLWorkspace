import React, { useEffect } from 'react';
import useFetch from "use-http";
import {
  Box, Button,
  Dialog, DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle
} from "@material-ui/core";

import _ from "lodash";

interface Context {
  teams: any;
  selectedTeam: any;
  saveSelectedTeam(team: React.SetStateAction<string>): void;
  WikiLink: string;
}

const Context = React.createContext<Context>({
  teams: [],
  selectedTeam: '',
  saveSelectedTeam: function(team: React.SetStateAction<string>) {},
  WikiLink: '',
});

export default Context;
interface ProviderProps {
  addGroupLink: string;
  WikiLink: string;
}
export const Provider: React.FC<ProviderProps> = ({addGroupLink,WikiLink ,children }) => {
  const fetchTeamsUrl = '/api/teams';
  const { data: teams } = useFetch(fetchTeamsUrl, { onMount: true });
  const [selectedTeam, setSelectedTeam] = React.useState<string>('');
  const saveSelectedTeam = (team: React.SetStateAction<string>) => {
    setSelectedTeam(team);
    localStorage.setItem('team',team.toString())
    window.location.reload()
  };
  useEffect(()=> {
    console.log("--------------->", WikiLink)
    if (localStorage.getItem('team')) {
      setSelectedTeam((String)(localStorage.getItem('team')))
    } else {
      setSelectedTeam(_.map(teams, 'id')[0]);
    }
  },[teams])
  const EmptyTeam: React.FC<ProviderProps> = () => {
    const onClick = () => {
      window.open(addGroupLink,"_blank");
    }
    return (
      <Box display="flex">
        <Dialog open>
          <DialogTitle style={{ color: 'red' }}>
            {"warning"}
          </DialogTitle>
          <DialogContent>
            <DialogContentText>
              {"You are not an authorized user for this cluster. Please request to join a security group by following the button below."}
            </DialogContentText>
          </DialogContent>
          <DialogActions>
            <Button onClick={onClick} color="primary">
              JOIN SG
            </Button>
          </DialogActions>
        </Dialog>
      </Box>
    )
  };
  if (teams !== undefined && teams.length === 0) {
    console.log(addGroupLink)
    console.log(WikiLink)
    return (

      <Context.Provider
        value={{ teams, selectedTeam ,saveSelectedTeam,WikiLink }}
        children={<EmptyTeam addGroupLink={addGroupLink} WikiLink={WikiLink}/>}
      />
    )
  }
  return (
    <Context.Provider
      value={{ teams, selectedTeam, saveSelectedTeam,WikiLink }}
      children={children}
    />
  );
};
