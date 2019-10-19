import React, {useEffect, useState} from "react";
import { Link } from "react-router-dom";
import useFetch from "use-http";
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

import {Cell, PieChart, Pie, ResponsiveContainer,Sector} from "recharts";
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
    margin: '0 auto',
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
    { name: "Unschedulable", value: reserved, color: deepOrange[400]},
  ];
  if (reserved === 0) {
    data = data.filter((item)=>item.name !== 'Reserved')
  }
  const styles = useStyles();
  const renderActiveShape = (props: any) => {
    const RADIAN = Math.PI / 180;
    const { cx, cy, midAngle, innerRadius, outerRadius, startAngle, endAngle,
      fill, payload, percent, value } = props;
    const sin = Math.sin(-RADIAN * midAngle);
    const cos = Math.cos(-RADIAN * midAngle);
    const sx = cx + (outerRadius + 10) * cos;
    const sy = cy + (outerRadius + 10) * sin;
    const mx = cx + (outerRadius + 30) * cos;
    const my = cy + (outerRadius + 30) * sin;
    const ex = mx + (cos >= 0 ? 1 : -1) * 22;
    const ey = my;
    const textAnchor = cos >= 0 ? 'start' : 'end';

    return (
      <g>
        <text x={cx} y={cy} dy={8} textAnchor="middle" fill={fill}>{payload.name}</text>
        <Sector
          cx={cx}
          cy={cy}
          innerRadius={innerRadius}
          outerRadius={outerRadius}
          startAngle={startAngle}
          endAngle={endAngle}
          fill={fill}
        />
        <Sector
          cx={cx}
          cy={cy}
          startAngle={startAngle}
          endAngle={endAngle}
          innerRadius={outerRadius + 6}
          outerRadius={outerRadius + 10}
          fill={fill}
        />
        <path d={`M${sx},${sy}L${mx},${my}L${ex},${ey}`} stroke={fill} fill="none"/>
        <circle cx={ex} cy={ey} r={2} fill={fill} stroke="none"/>
        <text x={ex + (cos >= 0 ? 1 : -1) * 12} y={ey} textAnchor={textAnchor} fill="#333">{`${value}`}</text>
        <text x={ex + (cos >= 0 ? 1 : -1) * 12} y={ey} dy={18} textAnchor={textAnchor} fill="#999">
          {`(Rate ${(percent * 100).toFixed(2)}%)`}
        </text>
      </g>
    );
  };
  const[activeIndex, setActiveIndex] = useState(0);
  const onPieEnter = (data: any, index: number) => {
    setActiveIndex(index)
  }
  return (
    <>
      <ResponsiveContainer  aspect={16/10} height={300} width='100%'>
        <PieChart>
          <Pie
            dataKey="value"
            isAnimationActive={isActive}
            activeIndex={activeIndex}
            activeShape={renderActiveShape}
            data={data}
            cx={200}
            // cy={200}
            innerRadius={60}
            outerRadius={80}
            fill="#8884d8"
            onMouseEnter={onPieEnter}
          >
            { data.map(({ name, color }) => <Cell key={name} fill={color}/>) }
          </Pie>
        </PieChart>
      </ResponsiveContainer>
    </>
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
  const fetchDiretoryUrl = `api/clusters/${cluster}`;
  const request = useFetch(fetchDiretoryUrl);
  const fetchDirectories = async () => {
    const data = await request.get('');
    const name = typeof email === 'string' ?  email.split('@', 1)[0] : email;
    setDataStorage(data.dataStorage);
    setWorkStorage(`${data.workStorage}/${name}`);
  }
  const fetchClusterStatusUrl = `/api`;
  const requestClusterStatus = useFetch(fetchClusterStatusUrl);
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
