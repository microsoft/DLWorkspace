import React from "react";
import {
  CircularProgress, createMuiTheme,
  MuiThemeProvider, Paper,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow, Typography, useTheme
} from "@material-ui/core";
import Iframe from "react-iframe";
import useCheckIsDesktop from "../../../utlities/layoutUtlities";
import {checkObjIsEmpty} from "../../../utlities/ObjUtlities";
import ServicesChips from "./ServicesChips";
import {red} from "@material-ui/core/colors";

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
            nodeStatus.map((ns: any) => {
              const gpuCap = checkObjIsEmpty(ns['gpu_capacity']) ? 0 :  (Number)(Object.values(ns['gpu_capacity'])[0]);
              const gpuUsed = checkObjIsEmpty(ns['gpu_used']) ? 0 : (Number)(Object.values(ns['gpu_used'])[0]);
              const availableGPU = gpuCap - gpuUsed;
              const status = ns['unschedulable'] ? "unschedulable" : "ok";
              let services: string[] = [];
              for (let service of ns['scheduled_service']) {
                services.push(`${service}`);
              }
              return  (
                <TableRow key={ns['name']}>
                  <TableCell>{ns['name']}</TableCell>
                  <TableCell>{ns['InternalIP']}</TableCell>
                  <TableCell>{gpuCap}</TableCell>
                  <TableCell>{gpuUsed}</TableCell>
                  <TableCell>{availableGPU}</TableCell>
                  <TableCell>{status}</TableCell>
                  <TableCell>
                    {
                      <ServicesChips services={services}/>
                    }
                  </TableCell>
                  <TableCell>
                    {
                      ns['pods'].map((pod: string)=>{
                        if (!pod.includes("!!!!!!")) {
                          return (
                            <Typography variant="subtitle2" component="b" gutterBottom>
                              {`[${pod}]`}
                            </Typography>
                          )
                        } else {
                          return (
                            <Typography variant="subtitle2" component="b" style={{ color:red[400] }} gutterBottom>
                              {`[${pod}]\n`}
                            </Typography>
                          )
                        }
                      })
                    }
                  </TableCell>
                </TableRow>
              )
            })
          }
        </TableBody>
      </Table>
    </MuiThemeProvider>
  )
}
