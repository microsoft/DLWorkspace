import React from "react";
import {
  CircularProgress,
  createMuiTheme,
  MuiThemeProvider, SvgIcon,Typography, useTheme
} from "@material-ui/core";
import useCheckIsDesktop from "../../../utlities/layoutUtlities";
import {checkObjIsEmpty, sumValues} from "../../../utlities/ObjUtlities";
import {red} from "@material-ui/core/colors";
import Tooltip from "@material-ui/core/Tooltip";
import IconButton from "@material-ui/core/IconButton";
import MaterialTable, {MTableToolbar} from "material-table";

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
      {
        nodeStatus ?  <MaterialTable
          title=""
          columns={[
            {title: 'Node Name', field: 'name'},
            {title: 'Node IP', field: 'InternalIP'},
            {title: 'GPU', field: 'gpu_capacity', render: (rowData: any) => <span>{checkObjIsEmpty(rowData['gpu_capacity']) ? 0 :  (Number)(sumValues(rowData['gpu_capacity']))}</span>, customSort: (a: any, b: any) => { return sumValues(a['gpu_capacity']) - sumValues(b['gpu_capacity'])}  },
            {title: 'Used', field: '', render: (rowData: any) => <span>{checkObjIsEmpty(rowData['gpu_used']) ? 0 :  (Number)(sumValues(rowData['gpu_used']))}</span>, customSort: (a: any, b: any) => { return sumValues(a['gpu_used']) - sumValues(b['gpu_used'])}},
            {title: 'Preemptible Used', field: '', render: (rowData: any) => <span>{checkObjIsEmpty(rowData['gpu_preemptable_used']) ? 0 :  (Number)(sumValues(rowData['gpu_preemptable_used']))}</span>, customSort: (a: any, b: any) => { return sumValues(a['gpu_preemptable_used']) - sumValues(b['gpu_preemptable_used'])}},
            {title: 'Available', field: '', render: (rowData: any) => <span>{(Number)(sumValues(rowData['gpu_allocatable'])) - (Number)(sumValues(rowData['gpu_used']))}</span>, customSort: (a: any, b: any) => { return ((Number)(sumValues(a['gpu_allocatable'])) - (Number)(sumValues(a['gpu_used']))) - (sumValues(b['gpu_allocatable']) - (Number)(sumValues(b['gpu_used'])) )} },
            {title: 'Status', field: '', render: (rowData: any) => <>
                 <Tooltip title={rowData['unschedulable'] ? "unschedulable" : "ok"}>
                   <IconButton color={!rowData['unschedulable'] ? "primary" : "secondary"} size="small">
                     <SvgIcon>
                       {!rowData['unschedulable'] ?  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"><path fill="none" d="M0 0h24v24H0z"/><path d="M9 16.2L4.8 12l-1.4 1.4L9 19 21 7l-1.4-1.4L9 16.2z"/></svg> :  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"><path clip-rule="evenodd" fill="none" d="M0 0h24v24H0z"/><path d="M22.7 19l-9.1-9.1c.9-2.3.4-5-1.5-6.9-2-2-5-2.4-7.4-1.3L9 6 6 9 1.6 4.7C.4 7.1.9 10.1 2.9 12.1c1.9 1.9 4.6 2.4 6.9 1.5l9.1 9.1c.4.4 1 .4 1.4 0l2.3-2.3c.5-.4.5-1.1.1-1.4z"/></svg>}
                     </SvgIcon>
                   </IconButton>
                 </Tooltip>
              </>, customSort:(a: any, b: any) => a['unschedulable'] - b['unschedulable']},
            {title: 'Pods', field: '', render: (rowData: any) => <>
                {
                  rowData['pods'].map((pod: string)=>{
                    if (!pod.includes("!!!!!!")) {
                      return (
                        <>
                          <Typography variant="subtitle2" component="span" gutterBottom>
                            {`[${pod}]`}
                          </Typography>
                          <br/>
                        </>
                      )
                    } else {
                      return (
                        <>
                          <Typography variant="subtitle2" component="span" style={{ color:red[400] }} gutterBottom>
                            {`[${pod.replace("!!!!!!", "")}]`}
                          </Typography>
                          <br/>
                        </>
                      )
                    }
                  })
                }
              </>}
          ]}
          data={nodeStatus}
          options={{filtering: false,paging: true, pageSizeOptions:[10],pageSize: 10,sorting: true}}
        /> :
          <CircularProgress/>
      }
    </MuiThemeProvider>
  )
}
