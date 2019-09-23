import React from "react";
import {
  Table,
  TableHead,
  TableRow, TableCell, TableBody, Radio
} from "@material-ui/core";
import {checkObjIsEmpty} from "../../../utlities/ObjUtlities";
import { TeamVCTitles } from "../../../Constants/TabsContants";

interface TeamVC {
  children?: React.ReactNode;
  vcStatus: any;
  selectedValue: string;
  handleChange: any;
}

export const TeamVirtualClusterStatus = (props: TeamVC) => {
  const{vcStatus,selectedValue,handleChange, children} = props;
  return (
    <Table size={"small"}>
      <TableHead>
        <TableRow>
          {
            TeamVCTitles.map((teamVCTitle)=>(
              <TableCell>{teamVCTitle}</TableCell>
            ))
          }
        </TableRow>
      </TableHead>
      <TableBody>
        {
          vcStatus ? vcStatus.map(( vcs: any, index: number) => {
            const gpuCapacity =  checkObjIsEmpty(Object.values(vcs['gpu_capacity'])) ? 0 : (String)(Object.values(vcs['gpu_capacity'])[0]);
            const gpuAvailable = checkObjIsEmpty (Object.values(vcs['gpu_avaliable'])) ? 0 : (String)(Object.values(vcs['gpu_avaliable'])[0]);
            const gpuUnschedulable = checkObjIsEmpty(Object.values(vcs['gpu_unschedulable'])) ? 0 : (String)(Object.values(vcs['gpu_unschedulable'])[0]);
            const gpuUsed =  checkObjIsEmpty(Object.values(vcs['gpu_used'])) ? 0 : (String)(Object.values(vcs['gpu_used'])[0]);
            return (
              <>
                <TableRow key={index}>
                  <TableCell key={vcs['ClusterName']}>
                    <Radio
                      checked={selectedValue === vcs['ClusterName']}
                      onChange={handleChange}
                      value={vcs['ClusterName']}
                      name={vcs['ClusterName']}/>
                    {vcs['ClusterName']}
                  </TableCell>
                  <TableCell key={gpuCapacity}>
                    {gpuCapacity}
                  </TableCell>
                  <TableCell key={gpuUnschedulable}>
                    {gpuUnschedulable}
                  </TableCell>
                  <TableCell key={gpuUsed}>
                    {gpuUsed}
                  </TableCell>
                  <TableCell key={gpuAvailable}>
                    {gpuAvailable}
                  </TableCell>
                  <TableCell key={vcs['AvaliableJobNum']}>
                    {vcs['AvaliableJobNum']}
                  </TableCell>
                </TableRow>
              </>
            )
          }) : null
        }

      </TableBody>
    </Table>
  )
}
