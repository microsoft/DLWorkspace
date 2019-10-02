import React from "react";
import {
  Table,
  TableHead,
  TableRow, TableCell, TableBody, Radio
} from "@material-ui/core";
import {checkObjIsEmpty, sumValues} from "../../../utlities/ObjUtlities";
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
            TeamVCTitles.map((teamVCTitle, index)=>(
              <TableCell key={index}>{teamVCTitle}</TableCell>
            ))
          }
        </TableRow>
      </TableHead>
      <TableBody>
        {
          vcStatus ? vcStatus.map(( vcs: any, index: number) => {
            const gpuCapacity =  checkObjIsEmpty(Object.values(vcs['gpu_capacity'])) ? 0 : (Number)(sumValues(vcs['gpu_capacity']));
            const gpuAvailable = checkObjIsEmpty (Object.values(vcs['gpu_avaliable'])) ? 0 : (Number)(sumValues(vcs['gpu_avaliable']));
            const gpuUnschedulable = checkObjIsEmpty(Object.values(vcs['gpu_unschedulable'])) ? 0 : (Number)(sumValues(vcs['gpu_unschedulable'])) ;
            const gpuUsed =  checkObjIsEmpty(Object.values(vcs['gpu_used'])) ? 0 :  (Number)(sumValues(vcs['gpu_used']));
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
