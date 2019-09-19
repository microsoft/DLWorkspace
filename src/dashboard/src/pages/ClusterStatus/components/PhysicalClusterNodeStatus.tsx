import React from "react";
import {
  CircularProgress, createMuiTheme,
  MuiThemeProvider, Paper,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow, useTheme
} from "@material-ui/core";
import Iframe from "react-iframe";
import useCheckIsDesktop from "../../../utlities/layoutUtlities";
import {checkObjIsEmpty} from "../../../utlities/ObjUtlities";
import ServicesChips from "./ServicesChips";

interface PhClusterNSType {
  nodeStatus: any;
}
const tableTheme = createMuiTheme({
  overrides: {
    MuiTableCell: {
      root: {
        paddingTop: 4,
        paddingBottom: 4,
        paddingLeft:2,
        paddingRight:4,
      }
    }
  }
});
export const PhysicalClusterNodeStatus = (props: PhClusterNSType) => {
  const theme = useTheme();
  const {nodeStatus} = props;
  return (
    <MuiThemeProvider theme={useCheckIsDesktop ? theme : tableTheme}>
      <Table size={ 'small'} >
        <TableHead>
          <TableRow>
            <TableCell>Node Name</TableCell>
            <TableCell>Node IP</TableCell>
            <TableCell>GPU Capacity</TableCell>
            <TableCell>Used GPU</TableCell>
            <TableCell>Available GPU</TableCell>
            <TableCell>Status</TableCell>
            <TableCell>Services</TableCell>
            <TableCell>Pods</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {
            nodeStatus.map((ns: any, index: number) => {
              const gpuCap = checkObjIsEmpty(ns['gpu_capacity']) ? 0 :  (Number)(Object.values(ns['gpu_capacity'])[0]);
              const gpuUsed = checkObjIsEmpty(ns['gpu_used']) ? 0 : (Number)(Object.values(ns['gpu_used'])[0]);
              const availableGPU = gpuCap - gpuUsed;
              const status = ns['unschedulable'] ? "unschedulable" : "ok";
              let services: string[] = [];
              for (let service of ns['scheduled_service']) {
                services.push(`${service}`);
              }
              let podStr = '';
              for (let pod of ns['pods']) {
                if (!pod.includes("!!!!!!")) {
                  podStr += `<b>[${pod}]</b>`;
                } else {
                  pod = pod.replace("!!!!!!","");
                  podStr += `<b  variant='h6' style="color:red">[${pod}]</b>`;
                }
                podStr += "<br/>";
              }
              return  (
                <TableRow key={index}>
                  <TableCell key="ns['name']">{ns['name']}</TableCell>
                  <TableCell key="ns['InternalIP']">{ns['InternalIP']}</TableCell>
                  <TableCell key="gpuCap">{gpuCap}</TableCell>
                  <TableCell key="gpuUsed">{gpuUsed}</TableCell>
                  <TableCell key="availableGPU">{availableGPU}</TableCell>
                  <TableCell key="status">{status}</TableCell>
                  <TableCell key="services">
                    {
                      <ServicesChips services={services}/>
                    }
                  </TableCell>
                  <TableCell key="podStr" dangerouslySetInnerHTML={{ __html: podStr }}></TableCell>
                </TableRow>
              )
            })
          }
        </TableBody>
      </Table>
    </MuiThemeProvider>
  )
}
