import * as React from 'react';
import {
  Tooltip,
  Switch,
  CircularProgress
} from "@material-ui/core";
import {MTableToolbar} from "material-table";
import SvgIconsMaterialTable from '../../../components/SvgIconsMaterialTable';

interface TeamUsr {
  userStatus: any;
  showCurrentUser: boolean;
  handleSwitch: any;
  currentCluster: string;
}

export const TeamVCUserStatus = (props: TeamUsr) => {
  const{userStatus, showCurrentUser,handleSwitch, currentCluster } = props;
  if (currentCluster === 'Lab-RR1-V100') {
    return (
      <>
        {
          userStatus ?  <SvgIconsMaterialTable
            title=""
            columns={[{title: 'Username', field: 'userName'},
              {title: 'Currently Allocated GPU', field: 'usedGPU',type:'numeric'},
              {title: 'Currently Allocated Preemptible GPU', field: 'preemptableGPU',type:'numeric'},
              {title: 'Currently Idle GPU', field: 'idleGPU',type:'numeric'},
            ]}
            data={showCurrentUser ? userStatus.filter((uc: any)=>uc['usedGPU'] > 0 && uc['userName'] !== 'Total') : userStatus}
            options={{filtering: false,paging: false,sorting: true}}
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
      </>
    )
  }
  return (
    <>
      {
        userStatus ?  <SvgIconsMaterialTable
          title=""
          columns={[{title: 'Username', field: 'userName'},
            {title: 'Currently Allocated GPU', field: 'usedGPU',type:'numeric'},
            {title: 'Currently Allocated Preemptible GPU', field: 'preemptableGPU',type:'numeric', render: (rowData: any) => <span>{rowData['preemptableGPU'] ? rowData['preemptableGPU'] : '0'}</span>},
          ]}
          data={showCurrentUser ? userStatus.filter((uc: any)=>uc['usedGPU'] > 0 && uc['userName'] !== 'Total') : userStatus}
          options={{filtering: false, paging: false, sorting: true}}
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
    </>
  )
}
