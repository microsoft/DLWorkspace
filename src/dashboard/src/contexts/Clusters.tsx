import React from "react";
import TeamContext from "./Teams";
import _ from 'lodash';
interface Context {
  clusters: any [];
  selectedCluster?: string;
  saveSelectedCluster(team: React.SetStateAction<string>): void;
}

const Context = React.createContext<Context>({
  clusters: [],
  selectedCluster: '',
  saveSelectedCluster: function(team: React.SetStateAction<string>) {}
});

export default Context;

export const Provider: React.FC = ({ children }) => {
  const { teams,selectedTeam } = React.useContext(TeamContext);
  const [clusters, setClusters] = React.useState<string[]>([]);
  const [selectedCluster, setSelectedCluster] = React.useState<string>('');
  const saveSelectedCluster = (cluster: React.SetStateAction<string>) => {
    setSelectedCluster(cluster);
  };
  React.useEffect( ()=>{
    if (teams && selectedTeam) {
      const filterClusters = teams.filter((team: any) => team.id === selectedTeam);

      for (let filterCluster of filterClusters) {
        setClusters(filterCluster.clusters)
        setSelectedCluster(_.map((filterCluster.clusters),'id')[0]);
      }
      console.log(clusters)
    }

  },[selectedTeam, teams]);

  return (
    <Context.Provider
      value={{ clusters, selectedCluster, saveSelectedCluster}}
      children={children}
    />
  );
};
