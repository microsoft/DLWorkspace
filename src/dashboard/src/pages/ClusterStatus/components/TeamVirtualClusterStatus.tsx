import React from "react";
import {
  Table,
  TableHead,
  TableRow,
  TableCell,
  TableBody,
  Radio,
  createMuiTheme,
  MuiThemeProvider,
  SvgIcon, Typography, CircularProgress, useTheme
} from "@material-ui/core";
import {checkObjIsEmpty, sumValues} from "../../../utlities/ObjUtlities";
import { TeamVCTitles } from "../../../Constants/TabsContants";
import useCheckIsDesktop from "../../../utlities/layoutUtlities";
import MaterialTable from "material-table";
import Tooltip from "@material-ui/core/Tooltip";
import IconButton from "@material-ui/core/IconButton";
import {red} from "@material-ui/core/colors";

interface TeamVC {
  children?: React.ReactNode;
  vcStatus: any;
  selectedValue: string;
  handleChange: any;
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

const renderData = (data: any) => {
  return (
    <span>
      {
        checkObjIsEmpty(Object.values(data)) ? 0 : (Number)(sumValues(data))
      }
    </span>
  )
}
export const TeamVirtualClusterStatus = (props: TeamVC) => {
  const{vcStatus,selectedValue,handleChange, children} = props;
  const theme = useTheme();
  return (
    <MuiThemeProvider theme={useCheckIsDesktop ? theme : tableTheme}>
      {
        vcStatus ?  <MaterialTable
          title=""
          columns={[
            {title: 'Name', field: 'ClusterName', render:(rowData: any)=><div><Radio
              checked={selectedValue === rowData['ClusterName']}
              onChange={handleChange}
              value={rowData['ClusterName']}
              name={rowData['ClusterName']}/>{rowData['ClusterName']}</div>},
            {title: 'Total GPU', field: '', render:(rowData: any)=>renderData(rowData['gpu_capacity'])},
            {title: 'Unschedulable GPU"', field: '', render:(rowData: any)=>renderData(rowData['gpu_unschedulable'])},
            {title: 'Used GPU"', field: '', render:(rowData: any)=>renderData(rowData['gpu_used'])},
            {title: 'Available GPU', field: '', render:(rowData: any)=><span>{ Number(sumValues(rowData['AvaliableJobNum'])) || 0}</span>}
          ]}
          data={vcStatus}
          options={{filtering: false,paging: true, pageSizeOptions:[10],sorting: true}}
        /> :
          <CircularProgress/>
      }
    </MuiThemeProvider>

  )
}
