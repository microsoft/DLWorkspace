import React from "react";
import {
  Container,
  Tooltip,
  Switch,
  CircularProgress
} from "@material-ui/core";
import useCheckIsDesktop from "../../../utlities/layoutUtlities";
import MaterialTable, {MTableToolbar} from "material-table";

interface TeamUsr {
  userStatus: any;
  showCurrentUser: boolean;
  handleSwitch: any;
}

export const TeamVCUserStatus = (props: TeamUsr) => {
  const{userStatus, showCurrentUser,handleSwitch,  } = props;
  return (
    <Container maxWidth={useCheckIsDesktop ? 'lg' : 'xs'}>
      {
        userStatus ?  <MaterialTable
          title=""
          columns={[{title: 'Username', field: 'userName'},
            {title: 'Currently Allocated GPU', field: 'usedGPU',type:'numeric'},
            {title: 'Currently Idle GPU', field: 'idleGPU',type:'numeric'},
            {title: 'Past Month Booked GPU Hour', field: 'booked',type:'numeric'},
            {title: 'Past Month Idle GPU Hour', field: 'idle',type:'numeric'},
            {title: 'Past Month Idle GPU Hour %', field: 'idle',type:'numeric', render: (rowData: any) => <span style={{ color: Math.floor((rowData['idle'] / rowData['booked']) * 100) > 50 ? "red" : "black" }}>{Math.floor((rowData['idle'] / rowData['booked']) * 100) || 0}</span>, customSort: (a: any, b: any) => {return Math.floor((a['idle'] / a['booked']) * 100) - Math.floor((b['idle'] / b['booked']) * 100)}}]} data={showCurrentUser ? userStatus.filter((uc: any)=>uc['usedGPU'] > 0) : userStatus}
          options={{filtering: false,paging: false,sorting: true, exportButton: true,exportFileName: 'Team_VC_User_Report'}}
          components={{
            Toolbar: props => (
              <div>
                <MTableToolbar {...props} />
                <Tooltip title="Show Current User">
                  <Switch
                    checked={showCurrentUser}
                    onChange={handleSwitch}
                  />
                </Tooltip>
              </div>
            )
          }}
        /> :
          <CircularProgress/>
      }
    </Container>
  )
}
