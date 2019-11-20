import React from "react";
import {MenuItem, TextField} from "@material-ui/core";
import {convertToArrayByKey} from "../../../utlities/ObjUtlities";


interface JobsSelectProps {
  children?: React.ReactNode;
  currentCluster: any;
  onClusterChange: any;
  clusters: any [];
}
export const JobsSelectByCluster = (props: JobsSelectProps) => {
  const { currentCluster,onClusterChange,clusters } = props;
  return (
    <TextField
      select
      label="Choose Cluster"
      fullWidth
      variant="filled"
      value={currentCluster}
      onChange={onClusterChange}
    >
      {Array.isArray(convertToArrayByKey(clusters,'id')) && convertToArrayByKey(clusters,'id').map((cluster: any, index: number) => (
        <MenuItem key={index} value={cluster}>{cluster}</MenuItem>
      ))}
    </TextField>
  )
}
