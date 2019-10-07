import React, { useEffect } from 'react';
import useFetch from "use-http/dist";
import {
  Box, Button,
  Dialog, DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle
} from "@material-ui/core";
import {Redirect} from "react-router";
import _ from "lodash";

interface Context {
  teams: any;
  selectedTeam: any;
  saveSelectedTeam(team: React.SetStateAction<string>): void;
}

const Context = React.createContext<Context>({
  teams: [],
  selectedTeam: '',
  saveSelectedTeam: function(team: React.SetStateAction<string>) {}
});

export default Context;
export const Provider: React.FC = ({ children }) => {
  const fetchTeamsUrl = '/api/teams';
  const [teams] = useFetch(fetchTeamsUrl, { onMount: true });
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
    // if (typeof(Storage) !== "undefined" && localStorage.getItem('team') === undefined) {
    //   setSelectedTeam(_.map(teams, 'id')[0]);
    //   localStorage.setItem('team',_.map(teams, 'id')[0])
    // }
  },[teams])
  const EmptyTeam: React.FC = () => {
    const onClick = () => {
      return (
        <Redirect to="/"/>
      )
    }
    return (
      <Box display="flex">
        <Dialog open>
          <DialogTitle>
            {"warning"}
          </DialogTitle>
          <DialogContent>
            <DialogContentText>
              {"Your name is number empty team"}
            </DialogContentText>
          </DialogContent>
          <DialogActions>
            <Button onClick={onClick} color="primary">
              Back
            </Button>
          </DialogActions>
        </Dialog>
      </Box>
    )
  };
  if (teams !== undefined && teams.length === 0) {
    return (
      <Context.Provider
        value={{ teams, selectedTeam, saveSelectedTeam }}
        children={EmptyTeam}
      />
    )
  }
  return (
    <Context.Provider
      value={{ teams, selectedTeam, saveSelectedTeam }}
      children={children}
    />
  );
};
