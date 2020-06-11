import * as React from 'react';
import {
  FunctionComponent,
  useContext
} from "react";

import { Box } from "@material-ui/core";

import ClustersContext from "../../contexts/Clusters";

import ClusterCard from "./ClusterCard";

const Home: FunctionComponent = () => {
  const { clusters } = useContext(ClustersContext);

  return (
    <Box display="flex" flexWrap="wrap" paddingX={2}>
      {clusters.map(({ id }) => (
        <Box key={id} width={360} padding={1}>
          <ClusterCard clusterId={id}/>
        </Box>
      ))}
    </Box>
  );
};

export default Home;
