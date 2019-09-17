import React from "react";

import { Box } from "@material-ui/core";
import ClustersContext from "../../contexts/Clusters";
import GPUCard from "./GPUCard";
import Content from "../../layout/Content";
import Drawer from "../../layout/Drawer/index";
import _ from 'lodash';
const Home: React.FC = () => {

  const { clusters } = React.useContext(ClustersContext);
  console.log(clusters)
  return (
    <>
      <Box display="flex" flexWrap="wrap" paddingTop={5}>
        {//const filterclusters = clusters.filter((cluster)=>(boolean)cluster["admin"]);
          clusters && _.map(clusters,'id').map((cluster) => (
            <Box key={cluster} maxWidth={360} padding={1}>
              <GPUCard cluster={cluster}/>
            </Box>
          ))}
      </Box>
    </>
  )
};

export default Home;
