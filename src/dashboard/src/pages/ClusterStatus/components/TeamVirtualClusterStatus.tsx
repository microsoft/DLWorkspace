import * as React from 'react';
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
import Tooltip from "@material-ui/core/Tooltip";
import IconButton from "@material-ui/core/IconButton";
import {red} from "@material-ui/core/colors";
import SvgIconsMaterialTable from '../../../components/SvgIconsMaterialTable';

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
        !data ? 0 :
          checkObjIsEmpty(Object.values(data))  ? 0 : (Number)(sumValues(data))
      }
    </span>
  )
}
export const TeamVirtualClusterStatus = (props: TeamVC) => {
  const{vcStatus,selectedValue,handleChange, children} = props;
  const theme = useTheme();
  const checkIsDesktop = useCheckIsDesktop()
  return (
    <MuiThemeProvider theme={checkIsDesktop ? theme : tableTheme}>
      {
        vcStatus.length > 0 ?  <SvgIconsMaterialTable
          title=""
          columns={[
            {title: 'Name', field: 'ClusterName', render:(rowData: any)=><div><Radio
              checked={selectedValue === rowData['ClusterName']}
              onChange={handleChange}
              value={rowData['ClusterName']}
              name={rowData['ClusterName']}/>{rowData['ClusterName']}</div>, customSort:(a, b) => a['ClusterName'].localeCompare(b['ClusterName'])},
            {title: 'Total GPU', field: '', render:(rowData: any)=>renderData(rowData['gpu_capacity']),customSort:(a, b) => sumValues(a['gpu_capacity']) - sumValues(b['gpu_capacity'])},
            {title: 'Unschedulable GPU', field: '', render:(rowData: any)=>renderData(rowData['gpu_unschedulable']), customSort:(a, b) => sumValues(a['gpu_unschedulable']) - sumValues(b['gpu_unschedulable'])},
            {title: 'Used GPU', field: '', render:(rowData: any)=>renderData(rowData['gpu_used']),customSort: (a, b) => sumValues(a['gpu_used']) - sumValues(b['gpu_used'])},
            {title: 'Preemptible Used GPU', field: '', render:(rowData: any)=>renderData(rowData['gpu_preemptable_used']), customSort: (a, b) => !a || !b ? -1 : sumValues(a['gpu_preemptable_used']) - sumValues(b['gpu_preemptable_used'])},
            {title: 'Available GPU', field: '', render:(rowData: any)=>renderData(rowData['gpu_avaliable']),customSort: (a, b) => sumValues(a['gpu_avaliable']) - sumValues(b['gpu_avaliable'])},
            {title: 'Active Jobs', field: '', render:(rowData: any)=><span>{ Number(sumValues(rowData['AvaliableJobNum'])) || 0}</span>, customSort: (a, b) => sumValues(a['AvaliableJobNum']) - sumValues(b['AvaliableJobNum'])}
          ]}
          data={vcStatus}
          options={{filtering: false,paging: true, pageSize: vcStatus.length < 10 ? vcStatus.length  : 10 ,pageSizeOptions:[10],sorting: true}}
        /> :
          <CircularProgress/>
      }
    </MuiThemeProvider>

  )
}
