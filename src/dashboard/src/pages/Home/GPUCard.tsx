import React, {useEffect, useState} from "react";
import { Link } from "react-router-dom";
import useFetch from "use-http/dist";
import {
  Button,
  Card,
  CardActions,
  CardContent,
  CardHeader,
  Divider,
  IconButton,
  InputAdornment,
  Menu,
  MenuItem,
  TextField,
  Tooltip
} from "@material-ui/core";
import { makeStyles, createStyles, useTheme, Theme } from "@material-ui/core/styles";
import { MoreVert, FileCopyRounded} from "@material-ui/icons";

import { Cell, PieChart, Pie, ResponsiveContainer } from "recharts";
import UserContext from "../../contexts/User";
import TeamsContext from '../../contexts/Teams';
import {green, lightGreen, deepOrange } from "@material-ui/core/colors";
import copy from 'clipboard-copy'
import {checkObjIsEmpty, sumValues} from "../../utlities/ObjUtlities";
import {DLTSSnackbar} from "../CommonComponents/DLTSSnackbar";
const useStyles = makeStyles((theme: Theme) => createStyles({
  avatar: {
    backgroundColor: theme.palette.secondary.main,
  },
  cardHeaderContent: {
    width: 0
  },
  textField: {
    marginLeft: theme.spacing(1),
    marginRight: theme.spacing(1),
  },
  chart: {
    padding: 3,
    backgroundColor: theme.palette.background.default,
  },
  dialogText: {
    color:green[400]
  },
  success: {
    backgroundColor: green[600],
  },
  container: {
    fontSize:'10.5px',
    paddingTop:'10px'
  }
}));

const ActionIconButton: React.FC<{cluster?: string}> = ({cluster}) => {
  const [open, setOpen] = React.useState(false);
  const iconButton = React.useRef<any>();
  const onIconButtonClick = React.useCallback(() => setOpen(true), [setOpen]);
  const onMenuClose = React.useCallback(() => setOpen(false), [setOpen]);

  return (
    <>
      <IconButton ref={iconButton} onClick={onIconButtonClick}>
        <MoreVert/>
      </IconButton>
      <Menu
        anchorEl={iconButton.current}
        anchorOrigin={{ horizontal: "right", vertical: "top" }}
        transformOrigin={{ horizontal: "right", vertical: "top" }}
        open={open}
        onClose={onMenuClose}
      >
        <MenuItem component={Link} to={"/cluster-status"}>Cluster Status</MenuItem>
        <MenuItem component={Link} to={`/jobs/${cluster}`}>View Jobs</MenuItem>
      </Menu>
    </>
  )
};

const Chart: React.FC<{
  available: number;
  used: number;
  reserved: number;
  isActive: boolean;

}> = ({ available, used, reserved ,isActive}) => {
  const theme = useTheme();
  let data = [
    { name: "Available", value: available, color: lightGreen[400] },
    { name: "Used", value: used, color: theme.palette.grey[500] },
    { name: "Reserved", value: reserved, color: deepOrange[400]},
  ];
  if (reserved === 0) {
    data = data.filter((item)=>item.name !== 'Reserved')
  }
  const styles = useStyles();
  return (
    <ResponsiveContainer aspect={16 / 11} height={300} width='100%' className={styles.container}>
      <PieChart>
        <Pie
          // hide={!isActive}
          isAnimationActive={isActive}
          data={data}
          dataKey="value"
          label={({ name, value }) => `${name} ${value}`}
          labelLine={false}
        >
          { data.map(({ name, color }) => <Cell key={name} fill={color}/>) }
        </Pie>
      </PieChart>
    </ResponsiveContainer>
  )
}

export const DirectoryPathTextField: React.FC<{
  label: string;
  value: string;
}> = ({ label, value }) => {
  const input = React.useRef<HTMLInputElement>(null);
  const [openCopyWarn, setOpenCopyWarn] = React.useState(false);
  const handleWarnClose = () => {
    setOpenCopyWarn(false);
  }
  const onMouseOver = React.useCallback(() => {
    if (input.current) {
      input.current.select();
    }
  }, [input])
  const onFocus = React.useCallback(() => {
    if (input.current) {
      input.current.select();
    }
  },
  [input]);
  const handleCopy = React.useCallback(() => {
    if (input.current) {
      copy(input.current.innerHTML).then(()=>{
        setOpenCopyWarn(true)
      })

    }
  },[input])
  return (
    <>
    <TextField
      inputRef={input}
      label={label}
      value={value}
      multiline
      rows={2}
      fullWidth
      variant="outlined"
      margin="dense"
      InputProps={{
        readOnly: true,
        endAdornment: (
          <InputAdornment position="end">
            <Tooltip title="Copy" placement="right">
              <IconButton>
                <FileCopyRounded/>
              </IconButton>
            </Tooltip>
          </InputAdornment>
        )
      }}
      onMouseOver={onMouseOver}
      onFocus={onFocus}
      onClick={handleCopy}
    />
    <DLTSSnackbar message={"Successfully copied"} autoHideDuration={500} open={openCopyWarn} handleWarnClose={handleWarnClose} />
    </>
  );
}

const GPUCard: React.FC<{ cluster: string }> = ({ cluster }) => {
  const styles = useStyles();
  const [activeJobs, setActiveJobs] = useState(0);
  const [available, setAvailable] = useState(0);
  const [used, setUsed] = useState(0);
  const [reversed, setReserved] = useState(0);
  const [workStorage, setWorkStorage ] = useState('');
  const [dataStorage, setDataStorage] = useState('');
  const [activate,setActivate] = useState(false);
  const { email } = React.useContext(UserContext);
  const {selectedTeam} = React.useContext(TeamsContext);
  const options = {
    onMount: true
  }
  const fetchDiretoryUrl = `api/clusters/${cluster}`;
  const request = useFetch(fetchDiretoryUrl,options);
  const fetchDirectories = async () => {
    const data = await request.get('');
    const name = typeof email === 'string' ?  email.split('@', 1)[0] : email;
    setDataStorage(data.dataStorage);
    setWorkStorage(`${data.workStorage}/${name}`);
  }
  const fetchClusterStatusUrl = `/api`;
  const requestClusterStatus = useFetch(fetchClusterStatusUrl, options);
  const fetchClusterStatus = async () => {
    setActivate(false);
    const data = await requestClusterStatus.get(`/teams/${selectedTeam}/clusters/${cluster}`);
    return data;
  }
  useEffect(()=>{
    fetchDirectories();
    fetchClusterStatus().then((res)=>{
      const availableGpu = !checkObjIsEmpty(res['gpu_avaliable']) ? (Number)(sumValues(res['gpu_avaliable'])) : 0;
      setAvailable(availableGpu);
      const usedGpu = !checkObjIsEmpty(res['gpu_used']) ? (Number)(sumValues(res['gpu_used'])) : 0;
      setUsed(usedGpu);
      const reversedGpu = !checkObjIsEmpty(res['gpu_unschedulable']) ? (Number)(sumValues(res['gpu_unschedulable'])) : 0;
      setReserved(reversedGpu);
      setActiveJobs((Number)(sumValues(res['AvaliableJobNum'])));
      setActivate(true);
    })
  },[selectedTeam]);
  return (
    <Card>
      <CardHeader
        title={cluster}
        titleTypographyProps={{
          component: "h3",
          variant: "body2",
          noWrap: true
        }}
        subheader={` ${activeJobs} Active Jobs`}
        action={<ActionIconButton cluster={cluster}/>}
        classes={{ content: styles.cardHeaderContent }}
      />
      <CardContent className={styles.chart}>
        <Chart available={available} used={used} reserved={reversed} isActive={activate} />
      </CardContent>
      <CardActions>
        <Button component={Link}
          to={{pathname: "/submission/training-cluster", state: { cluster } }}
          size="small" color="secondary"
        >
          Submit Training Job
        </Button>
        <Button component={Link}
          to={{pathname: "/submission/data", state: { cluster } }}
          size="small" color="secondary"
        >
          Submit Data Job
        </Button>
      </CardActions>
      <Divider/>
      <CardContent>
        <DirectoryPathTextField
          label="Work Directory"
          value={workStorage}
        />
        <DirectoryPathTextField
          label="Data Directory"
          value={dataStorage}
        />
      </CardContent>
    </Card>
  );
};

export default GPUCard;
