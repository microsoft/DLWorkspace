import React, {useState} from "react";

import {
  Card,
  CardHeader,
  CardContent,
  CardActions,
  Grid,
  Container,
  TextField,
  FormControlLabel,
  Checkbox,
  Button,
  Divider,
  Chip,
  Collapse,
  Typography,
  Table,
  TableHead,
  TableRow,
  TableCell,
  TableBody,
  Switch,
  MenuItem,
  SvgIcon, useMediaQuery
} from "@material-ui/core";
import Tooltip from '@material-ui/core/Tooltip';
import { makeStyles, createStyles } from "@material-ui/core/styles";
import { Info, Delete, Add } from "@material-ui/icons";
import { withRouter } from "react-router";
import IconButton from '@material-ui/core/IconButton';
import { useGet, usePost, usePut } from "use-http";
import { join } from 'path';

import ClusterSelectField from "./components/ClusterSelectField";
import UserContext from "../../contexts/User";
import ClustersContext from '../../contexts/Clusters';
import TeamsContext from "../../contexts/Teams";
import theme, { Provider as MonospacedThemeProvider } from "../../contexts/MonospacedTheme";
import useFetch, {useDelete} from "use-http/dist";
import {BarChart, Bar, XAxis, YAxis, CartesianGrid}  from "recharts";
import Paper, { PaperProps } from '@material-ui/core/Paper';
import Draggable from 'react-draggable'
import {TransitionProps} from "@material-ui/core/transitions";
import Slide from "@material-ui/core/Slide";
import {green, grey, red} from "@material-ui/core/colors";
import {DLTSDialog} from "../CommonComponents/DLTSDialog";
import {
  SUCCESSFULSUBMITTED,
  SUCCESSFULTEMPLATEDELETE, SUCCESSFULTEMPLATEDSAVE
} from "../../Constants/WarnConstants";
import {DLTSSnackbar} from "../CommonComponents/DLTSSnackbar";

interface EnvironmentVariable {
  name: string;
  value: string;
}

const useStyles = makeStyles(() =>
  createStyles({
    container: {
      margin: "auto"
    },
    submitButton: {
      marginLeft: "auto"
    }
  })
);

const sanitizePath = (path: string) => {
  path = join('/', path);
  path = join('.', path);
  return path;
}
const Training: React.ComponentClass = withRouter(({ history }) => {
  const { selectedCluster,saveSelectedCluster } = React.useContext(ClustersContext);
  const { email, uid } = React.useContext(UserContext);
  const { teams, selectedTeam }= React.useContext(TeamsContext);
  //const team = 'platform';
  const [showGPUFragmentation, setShowGPUFragmentation] = React.useState(false)
  const [prometheusUrl, setPrometheusUrl] = React.useState('');
  const [name, setName] = React.useState("");
  const [gpuFragmentation, setGpuFragmentation] = React.useState<any[]>([]);
  const onNameChange = React.useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      setName(event.target.value);
    },
    [setName]
  );
  const team = React.useMemo(() => {
    if (teams == null) return;
    if (selectedTeam == null) return;
    return teams.filter((team: any) => team.id === selectedTeam)[0];
  }, [teams, selectedTeam]);
  const cluster = React.useMemo(() => {
    if (team == null) return;
    if (selectedCluster == null) return;
    return team.clusters.filter((cluster: any) => cluster.id === selectedCluster)[0];
  }, [team, selectedCluster]);
  const gpuModel = React.useMemo(() => {
    if (cluster == null) return;
    return Object.keys(cluster.gpus)[0];
  }, [cluster]);
  const gpusPerNode = React.useMemo(() => {
    if (cluster == null || gpuModel == null) return;
    return cluster.gpus[gpuModel].perNode;
  }, [cluster, gpuModel]);

  const [templates, templatesLoading, templatesError, getTemplates] = useGet('/api');
  React.useEffect(() => {
    getTemplates(`/teams/${selectedTeam}/templates`);
  }, [getTemplates, selectedTeam]);

  const [type, setType] = React.useState("RegularJob");
  const onTypeChange = React.useCallback(
    (event: React.ChangeEvent<{ value: unknown }>) => {
      setType(event.target.value as string);
    },
    [setType]
  );

  const [preemptible, setPreemptible] = React.useState(false);
  const onPreemptibleChange = React.useCallback(
    (event: React.ChangeEvent<{ value: unknown }>) => {
      setPreemptible(event.target.value === 'true');
    },
    [setPreemptible]
  );

  const [gpus, setGpus] = React.useState(0);
  const onGpusChange = React.useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      let value = event.target.valueAsNumber || 0;
      if (value < 0) { value = 0; }
      if (value > 0) { value = 26; }
      setGpus(event.target.valueAsNumber);
    },
    [setGpus]
  );

  const [workers, setWorkers] = React.useState(0);
  const onWorkersChange = React.useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      let value = event.target.valueAsNumber || 0;
      if (value < 0) { value = 0; }
      if (value > 0) { value = 26; }
      setWorkers(event.target.valueAsNumber);
    },
    [setWorkers]
  );

  const [image, setImage] = React.useState("");
  const onImageChange = React.useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      setImage(event.target.value);
    },
    [setImage]
  );

  const [command, setCommand] = React.useState("");
  const onCommandChange = React.useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      setCommand(event.target.value);
    },
    [setCommand]
  );

  const [interactivePorts, setInteractivePorts] = React.useState("");
  const onInteractivePortsChange = React.useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      setInteractivePorts(event.target.value);
    },
    [setInteractivePorts]
  );

  const [ssh, setSsh] = React.useState(false);
  const onSshChange = React.useCallback(
    (event: unknown, checked: boolean) => {
      setSsh(checked);
    },
    [setSsh]
  );

  const [ipython, setIpython] = React.useState(false);
  const onIpythonChange = React.useCallback(
    (event: unknown, checked: boolean) => {
      setIpython(checked);
    },
    [setIpython]
  );

  const [tensorboard, setTensorboard] = React.useState(false);
  const onTensorboardChange = React.useCallback(
    (event: unknown, checked: boolean) => {
      setTensorboard(checked);
    },
    [setTensorboard]
  );

  const [advanced, setAdvanced] = React.useState(false);
  const onAdvancedClick = () => {
    setAdvanced(!advanced);
  }

  const [workPath, setWorkPath] = React.useState("");
  const onWorkPathChange = React.useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      setWorkPath(event.target.value);
    },
    [setWorkPath]
  )

  const [enableWorkPath, setEnableWorkPath] = React.useState(true);
  const onEnableWorkPathChange = React.useCallback(
    (event: unknown, checked: boolean) => {
      setEnableWorkPath(checked);
    },
    [setEnableWorkPath]
  );

  const [dataPath, setDataPath] = React.useState("");
  const onDataPathChange = React.useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      setDataPath(event.target.value);
    },
    [setDataPath]
  )

  const [enableDataPath, setEnableDataPath] = React.useState(true);
  const onEnableDataPathChange = React.useCallback(
    (event: unknown, checked: boolean) => {
      setEnableDataPath(checked);
    },
    [setEnableDataPath]
  );

  const [jobPath, setJobPath] = React.useState("");
  const onJobPathChange = React.useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      setJobPath(event.target.value);
    },
    [setJobPath]
  )

  const [enableJobPath, setEnableJobPath] = React.useState(true);
  const onEnableJobPathChange = React.useCallback(
    (event: unknown, checked: boolean) => {
      setEnableJobPath(checked);
    },
    [setEnableJobPath]
  );
  const [showSaveTemplate, setSaveTemplate] = React.useState(false);
  const [environmentVariables, setEnvironmentVariables] = React.useState<EnvironmentVariable[]>([]);
  const onEnvironmentVariableNameChange = React.useCallback(
    (index: number) => (event: React.ChangeEvent<HTMLInputElement>) => {
      const newEnvironmentVariables = environmentVariables.slice()
      environmentVariables[index].name = event.target.value;
      setEnvironmentVariables(newEnvironmentVariables);
    },
    [environmentVariables]
  );
  const onEnvironmentVariableValueChange = React.useCallback(
    (index: number) => (event: React.ChangeEvent<HTMLInputElement>) => {
      const newEnvironmentVariables = environmentVariables.slice()
      environmentVariables[index].value = event.target.value;
      setEnvironmentVariables(newEnvironmentVariables);
    },
    [environmentVariables]
  );
  const onRemoveEnvironmentVariableClick = React.useCallback(
    (index: number) => () => {
      const newEnvironmentVariables = environmentVariables.slice();
      newEnvironmentVariables.splice(index, 1);
      setEnvironmentVariables(newEnvironmentVariables)
    },
    [environmentVariables]
  )
  const onAddEnvironmentVariableClick = React.useCallback(() => {
    setEnvironmentVariables(
      environmentVariables.concat(
        [{ name: "", value: "" }]));
  }, [environmentVariables]);

  const [database, setDatabase] = React.useState(false);
  // const onDatabaseClick = React.useCallback(() => {
  //   setDatabase(true);
  // }, []);
  const onDatabaseClick = () => {
    setDatabase(!database);
  }


  const [saveTemplateName, setSaveTemplateName] = React.useState("");
  const onSaveTemplateNameChange = React.useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      setSaveTemplateName(event.target.value);
    },
    [setSaveTemplateName]
  );

  const [saveTemplateDatabase, setSaveTemplateDatabase] = React.useState("user");
  const onSaveTemplateDatabaseChange = React.useCallback(
    (event: React.ChangeEvent<{ value: unknown }>) => {
      setSaveTemplateDatabase(event.target.value as string);
    },
    [setSaveTemplateDatabase]
  );
  const { put: saveTemplate } = usePut('/api')
  const {delete: deleteTemplate} = useDelete('/api');
  const onSaveTemplateClick = async () => {
    try {
      const template = {
        name,
        type,
        gpus,
        workers,
        image,
        command,
        workPath,
        enableWorkPath,
        dataPath,
        enableDataPath,
        jobPath,
        enableJobPath,
        environmentVariables,
        ssh,
        ipython,
        tensorboard,
      };
      const url = `/teams/${selectedTeam}/templates/${saveTemplateName}?database=${saveTemplateDatabase}`;
      await saveTemplate(url, template);
      setSaveTemplate(true)
    } catch (error) {
      alert('Failed to save the template, check console (F12) for technical details.')
      console.error(error);
    }
  };
  const [showDeleteTemplate, setShowDeleteTemplate] = useState(false)
  const onDeleteTemplateClick = async () => {
    try {
      const template = {
        name,
        type,
        gpus,
        workers,
        image,
        command,
        workPath,
        enableWorkPath,
        dataPath,
        enableDataPath,
        jobPath,
        enableJobPath,
        environmentVariables,
        ssh,
        ipython,
        tensorboard,
      };
      const url = `/teams/${selectedTeam}/templates/${saveTemplateName}?database=${saveTemplateDatabase}`;
      await deleteTemplate(url);
      console.log(await deleteTemplate(url,template))
      setShowDeleteTemplate(true)
    } catch (error) {
      alert('Failed to delete the template, check console (F12) for technical details.')
      console.error(error);
    }
  }
  const [json, setJson] = React.useState('-1');
  const onTemplateChange = React.useCallback(
    (event: React.ChangeEvent<{ value: unknown }>) => {
      setJson(event.target.value as string)
      if (event.target.value == -1) {
        setName("");
        setType("RegularJob");
        setGpus(0);
        setWorkers(0);
        setImage("");
        setCommand("");
        setWorkPath("");
        setEnableWorkPath(true);
        setDataPath("");
        setEnableDataPath(true);
        setJobPath("");
        setEnableJobPath(true);
        setEnvironmentVariables([]);
        setSsh(false);
        setIpython(false);
        setTensorboard(false);
      } else {
        const {
          name,
          type,
          gpus,
          workers,
          image,
          command,
          workPath,
          enableWorkPath,
          dataPath,
          enableDataPath,
          jobPath,
          enableJobPath,
          environmentVariables,
          ssh,
          ipython,
          tensorboard,
        } = JSON.parse(event.target.value as string);
        console.log('jobpath', jobPath)
        if (name !== undefined) setName(name);
        if (type !== undefined) setType(type);
        if (gpus !== undefined) setGpus(gpus);
        if (workers !== undefined) setWorkers(workers);
        if (image !== undefined) setImage(image);
        if (command !== undefined) setCommand(command);
        if (workPath !== undefined) setWorkPath(workPath);
        if (enableWorkPath !== undefined) setEnableWorkPath(enableWorkPath);
        if (dataPath !== undefined) setDataPath(dataPath);
        if (enableDataPath !== undefined) setEnableDataPath(enableDataPath);
        if (jobPath !== undefined) setJobPath(jobPath);
        if (enableJobPath !== undefined) setEnableJobPath(enableJobPath);
        if (environmentVariables !== undefined) setEnvironmentVariables(environmentVariables);
        if (ssh !== undefined) setSsh(ssh);
        if (ipython !== undefined) setIpython(ipython);
        if (tensorboard !== undefined) setTensorboard(tensorboard);
      }
    },
    []
  );

  const [
    postJobData,
    postJobLoading,
    postJobError,
    postJob
  ] = usePost('/api');
  const [
    postEndpointsData,
    postEndpointsLoading,
    postEndpointsError,
    postEndpoints
  ] = usePost('/api');

  const submittable = React.useMemo(() => {
    if (!gpuModel) return false;
    if (!selectedTeam) return false;
    if (!name) return false;
    if (!image) return false;
    if (!command.trim()) return false;
    return true;
  }, [gpuModel, selectedTeam, name, image, command]);
  const [open, setOpen] = React.useState(false);
  const onSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    if (!submittable) return;

    const job: any = {
      userName: email,
      userId: uid,
      jobType: 'training',
      gpuType: gpuModel,
      vcName: selectedTeam,
      containerUserId: 0,
      jobName: name,
      jobtrainingtype: type,
      preemptionAllowed: preemptible ? 'True' : 'False',
      image,
      cmd: command,
      workPath: sanitizePath(workPath || ''),
      enableworkpath: enableWorkPath,
      dataPath: sanitizePath(dataPath || ''),
      enabledatapath: enableDataPath,
      jobPath: jobPath || '',
      enablejobpath: enableJobPath,
      env: environmentVariables,
      hostNetwork : type === 'PSDistJob' ? true : false,
      isPrivileged : type === 'PSDistJob' ? true : false,
    };

    let totalGpus = gpus;
    if (type === 'PSDistJob') {
      job.numps = 1;
      job.resourcegpu = gpusPerNode;
      job.numpsworker = workers;
      totalGpus = gpusPerNode * workers;
    } else {
      job.resourcegpu = gpus;
    }

    // if (totalGpus > (cluster.userQuota)) {
    //   if (!window.confirm('Your job will be using gpus more than the quota.\nProceed?')) {
    //     return;
    //   }
    // }

    if (type === 'PSDistJob') {
      // Check GPU fragmentation
      let workersNeeded = workers;
      console.log(gpuFragmentation)
      for (const { metric, value } of gpuFragmentation) {
        if (Number(metric['gpu_available']) >= gpusPerNode) {
          workersNeeded -= (Number(value[1]) || 0);
        }
        if (workersNeeded <= 0) break;
      }
      if (workersNeeded > 0) {
        if (!window.confirm('There won\'t be enough workers match your request.\nProceed?')) {
          return;
        }
      }
    }
    postJob(`/clusters/${selectedCluster}/jobs`, job);
  }; // Too many dependencies, do not cache.

  const jobId = React.useRef<string>();

  React.useEffect(() => {
    if (postJobData == null) return;

    jobId.current = postJobData['jobId'];
    const endpoints = [];

    for (const port of interactivePorts.split(',')) {
      const portNumber = Number(port)
      if (portNumber >= 40000 && portNumber <= 49999) {
        endpoints.push({
          name: `port-${portNumber}`,
          podPort: portNumber
        });
      }
    }

    if (ssh) endpoints.push('ssh');
    if (ipython) endpoints.push('ipython');
    if (tensorboard) endpoints.push('tensorboard');

    if (endpoints.length > 0) {
      postEndpoints(`/clusters/${selectedCluster}/jobs/${jobId.current}/endpoints`, { endpoints });
    } else {
      history.push(`/job/${selectedTeam}/${selectedCluster}/${jobId.current}`);
    }
  }, [postJobData, postEndpoints, ssh, ipython, tensorboard, interactivePorts, history, selectedCluster]);
  const fetchPrometheusUrl = `/api/clusters`;
  const request = useFetch(fetchPrometheusUrl);
  const fetchPrometheus = async () => {
    const {prometheus} = await request.get(`/${selectedCluster}`);
    setPrometheusUrl(prometheus);
  }
  const handleCloseGPUGramentation = () => {
    setShowGPUFragmentation(false);
  }

  React.useEffect(() => {
    fetchPrometheus()
    if (postEndpointsData) {
      setOpen(true);
      setTimeout(()=>{
        history.push(`/job/${selectedTeam}/${selectedCluster}/${jobId.current}`);
      },2000)

    }
  }, [history, postEndpointsData, selectedCluster])

  React.useEffect(() => {
    if (postJobError) {
      alert('Job submission failed')
    }
  }, [postJobError])

  React.useEffect(() => {
    if (postEndpointsError) {
      alert('Enable endpoints failed')
    }
  }, [postEndpointsError])


  const handleClickOpen = () => {
    setShowGPUFragmentation(true)
  }
  const handleClose = () => {
    setOpen(false)
    setSaveTemplate(false)
    setShowDeleteTemplate(false)
  }
  React.useEffect(() => {
    if (!prometheusUrl) return;
    let getNodeGpuAva = `${prometheusUrl}/prometheus/api/v1/query?`;
    const params = new URLSearchParams({
      query:'count_values("gpu_available", k8s_node_gpu_available)'
    });
    fetch(getNodeGpuAva+params).then(async (res: any) => {
      const {data} = await res.json();
      const result = data['result'];
      const sortededResult = result.sort((a: any, b: any)=>a['metric']['gpu_available'] - b['metric']['gpu_available']);
      setGpuFragmentation(sortededResult)
    })
  }, [prometheusUrl])

  const isDesktop = useMediaQuery(theme.breakpoints.up("sm"));

  const showMessage = (open: boolean,showDeleteTemplate: boolean,showSaveTemplate: boolean) => {
    let message = '';
    if (open) {
      message = SUCCESSFULSUBMITTED;
    }
    if (showDeleteTemplate) {
      message = SUCCESSFULTEMPLATEDELETE;
    }
    if (showSaveTemplate) {
      message = SUCCESSFULTEMPLATEDSAVE;
    }
    return message;
  }

  const styleSnack={backgroundColor:showDeleteTemplate ? red[400] : green[400]};
  return (

    <Container maxWidth={isDesktop ? 'lg' : 'xs'}>
      <DLTSDialog open={showGPUFragmentation}
        message={null}
        handleClose={handleCloseGPUGramentation}
        handleConfirm={null} confirmBtnTxt={null} cancelBtnTxt={null}
        title={"View Cluster GPU Status Per Node"}
        titleStyle={{color:grey[400]}}
      >
        <BarChart width={500} height={600} data={gpuFragmentation}>
          <CartesianGrid strokeDasharray="10 10"/>
          <XAxis dataKey={"metric['gpu_available']"} label={{value: 'Available gpu count', offset:0,position:'insideBottom'}}>
          </XAxis>
          <YAxis label={{value: 'Node count', angle: -90, position: 'insideLeft'}} />
          <Bar dataKey="value[1]" fill="#8884d8" />
        </BarChart>
      </DLTSDialog>
      <form onSubmit={onSubmit}>
        <Card>
          <CardHeader title="Submit Training Job"/>
          <Divider/>
          <CardContent>
            <Grid
              container
              wrap="wrap"
              spacing={1}
            >
              <Grid item xs={12} sm={6}>
                <ClusterSelectField
                  data-test="cluster-item"
                  fullWidth
                  cluster={selectedCluster}
                  onClusterChange={saveSelectedCluster}
                />
                <Tooltip title="View Cluster GPU Status Per Node">
                  <IconButton color="secondary" size="small" onClick={handleClickOpen} aria-label="delete">
                    <SvgIcon>
                      <path d="M5 9.2h3V19H5zM10.6 5h2.8v14h-2.8zm5.6 8H19v6h-2.8z"/><path fill="none" d="M0 0h24v24H0z"/>
                    </SvgIcon>
                  </IconButton>
                </Tooltip>
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  label="Job Name"
                  fullWidth
                  variant="filled"
                  value={name}
                  onChange={onNameChange}
                />
              </Grid>
              <Grid item xs={12}>
                <TextField
                  disabled={!Array.isArray(templates)}
                  select
                  label="Job Template"
                  fullWidth
                  variant="filled"
                  value={json}
                  onChange={onTemplateChange}
                >
                  <MenuItem value={-1} divider>None (Apply a Template)</MenuItem>
                  {Array.isArray(templates) && templates.sort((a,b)=>a.name.localeCompare(b.name)).map(({ name, json }: any, index: number) => (
                    <MenuItem key={index} value={json}>{name}</MenuItem>
                  ))}
                </TextField>
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  select
                  label="Job Type"
                  fullWidth
                  variant="filled"
                  value={type}
                  onChange={onTypeChange}
                >
                  <MenuItem value="RegularJob">Regular Job</MenuItem>
                  <MenuItem value="PSDistJob">Distirbuted Job</MenuItem>
                  <MenuItem value="InferenceJob">Inference Job</MenuItem>
                </TextField>
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  select
                  label="Preemptible Job"
                  fullWidth
                  variant="filled"
                  value={String(preemptible)}
                  onChange={onPreemptibleChange}
                >
                  <MenuItem value="false">NO</MenuItem>
                  <MenuItem value="true">YES</MenuItem>
                </TextField>
              </Grid>
              { (type === 'RegularJob' ||  type === 'InferenceJob') && (
                <Grid item xs={12}>
                  <TextField
                    type="number"
                    error={gpus > (type === 'InferenceJob' ? Number.MAX_VALUE : gpusPerNode)}
                    label="Number of GPUs"
                    fullWidth
                    variant="filled"
                    value={gpus}
                    onChange={onGpusChange}
                  />
                </Grid>
              )}
              { type === 'PSDistJob'  && (
                <Grid item xs={12} sm={6}>
                  <TextField
                    type="number"
                    label="Number of Nodes"
                    fullWidth
                    variant="filled"
                    value={workers}
                    onChange={onWorkersChange}
                  />
                </Grid>
              )}
              { type === 'PSDistJob' && (
                <Grid item xs={12} sm={6}>
                  <TextField
                    disabled
                    type="number"
                    label="Total Number of GPUs"
                    value = {workers * gpusPerNode}
                    fullWidth
                    variant="filled"
                  />
                </Grid>
              )}
              <Grid item xs={12}>
                <TextField
                  label="Docker Image"
                  fullWidth
                  variant="filled"
                  value={image}
                  onChange={onImageChange}
                />
              </Grid>
              <Grid item xs={12}>
                <MonospacedThemeProvider>
                  <TextField
                    multiline
                    label="Command"
                    fullWidth
                    variant="filled"
                    rows="10"
                    value={command}
                    onChange={onCommandChange}
                  />
                </MonospacedThemeProvider>
              </Grid>
              <Grid item xs={12}>
                <TextField
                  label="Interactive Ports"
                  placeholder="40000 - 49999. Separated by comma."
                  fullWidth
                  variant="filled"
                  rows="10"
                  value={interactivePorts}
                  onChange={onInteractivePortsChange}
                />
              </Grid>
              <Grid item xs={4} container justify="center">
                <FormControlLabel
                  control={<Checkbox />}
                  label="SSH"
                  checked={ssh}
                  onChange={onSshChange}
                />
              </Grid>
              <Grid item xs={4} container justify="center">
                <FormControlLabel
                  control={<Checkbox />}
                  label="iPython"
                  checked={ipython}
                  onChange={onIpythonChange}
                />
              </Grid>
              <Grid item xs={4} container justify="center">
                <FormControlLabel
                  control={<Checkbox />}
                  label={<>{"Tensorboard "}<Info fontSize="inherit"/></>}
                  checked={tensorboard}
                  onChange={onTensorboardChange}
                />
              </Grid>
              <Grid item xs={12} container justify="flex-end">
                <Chip
                  icon={<Info/>}
                  label="Tensorboard will listen on directory ~/tensorboard/<JobId>/logs inside docker container."
                />
              </Grid>
            </Grid>
          </CardContent>
          <Collapse in={advanced}>
            <Divider/>
            <CardContent>
              <Typography component="span" variant="h6">Mount Directories</Typography>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Path in Container</TableCell>
                    <TableCell>Path on Host Machine / Storage Server</TableCell>
                    <TableCell align="center">Enable</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  <TableRow>
                    <TableCell>/work</TableCell>
                    <TableCell>
                      <TextField
                        label="Work Path"
                        fullWidth
                        margin="dense"
                        variant="filled"
                        value={workPath}
                        onChange={onWorkPathChange}
                      />
                    </TableCell>
                    <TableCell align="center">
                      <Switch
                        value={enableWorkPath}
                        checked={enableWorkPath}
                        onChange={onEnableWorkPathChange}
                      />
                    </TableCell>
                    <TableCell align="center">
                    </TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell>/data</TableCell>
                    <TableCell>
                      <TextField
                        label="Data Path"
                        fullWidth
                        margin="dense"
                        variant="filled"
                        value={dataPath}
                        onChange={onDataPathChange}
                      />
                    </TableCell>
                    <TableCell align="center">
                      <Switch
                        value={enableDataPath}
                        checked={enableDataPath}
                        onChange={onEnableDataPathChange}
                      />
                    </TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell>/job</TableCell>
                    <TableCell>
                      <TextField
                        label="Job Path"
                        fullWidth
                        margin="dense"
                        variant="filled"
                        value={jobPath}
                        onChange={onJobPathChange}
                      />
                    </TableCell>
                    <TableCell align="center">
                      <Switch
                        value={enableJobPath}
                        checked={enableDataPath}
                        onChange={onEnableJobPathChange}
                      />
                    </TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            </CardContent>
            <CardContent>
              <Typography component="span" variant="h6">Environment Variables</Typography>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Name</TableCell>
                    <TableCell>Value</TableCell>
                    <TableCell/>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {
                    environmentVariables.map(({ name, value }, index) => (
                      <TableRow key={index}>
                        <TableCell>
                          <TextField
                            label="Environment Variable Name"
                            fullWidth
                            margin="dense"
                            variant="filled"
                            value={name}
                            onChange={onEnvironmentVariableNameChange(index)}
                          />
                        </TableCell>
                        <TableCell>
                          <TextField
                            label="Environment Variable Value"
                            fullWidth
                            margin="dense"
                            variant="filled"
                            value={value}
                            onChange={onEnvironmentVariableValueChange(index)}
                          />
                        </TableCell>
                        <TableCell align="center">
                          <IconButton size="small" color="secondary" onClick={onRemoveEnvironmentVariableClick(index)}>
                            <Delete/>
                          </IconButton>
                        </TableCell>
                      </TableRow>
                    ))
                  }
                  <TableRow>
                    <TableCell/>
                    <TableCell/>
                    <TableCell align="center">
                      <IconButton size="small" color="secondary" onClick={onAddEnvironmentVariableClick}>
                        <Add/>
                      </IconButton>
                    </TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            </CardContent>
          </Collapse>
          <Collapse in={database}>
            <Divider/>
            <CardContent>
              <Typography component="span" variant="h6">Database Management</Typography>
              <Grid container wrap="wrap" spacing={1}>
                <Grid item xs={12} sm={6}>
                  <TextField
                    label="Template name"
                    fullWidth
                    variant="filled"
                    value={saveTemplateName}
                    onChange={onSaveTemplateNameChange}
                  />
                </Grid>
                <Grid item xs>
                  <TextField
                    label="Database"
                    select
                    fullWidth
                    variant="filled"
                    value={saveTemplateDatabase}
                    onChange={onSaveTemplateDatabaseChange}
                  >
                    <MenuItem value="user">user</MenuItem>
                    <MenuItem value="team">team</MenuItem>
                  </TextField>
                </Grid>
                <Button type="button" color="primary" onClick={onSaveTemplateClick}>Save</Button>
                <Button type="button" color="secondary" onClick={onDeleteTemplateClick}>Delete</Button>
              </Grid>
            </CardContent>
          </Collapse>
          <Divider/>
          <CardActions>
            <Grid item xs={12} container justify="space-between">
              <Grid item xs container>
                <Button type="button" color="secondary"  onClick={onAdvancedClick}>Advanced</Button>
                <Button type="button" color="secondary"  onClick={onDatabaseClick}>Database</Button>
              </Grid>
              <Button type="submit" color="primary" variant="contained" disabled={!submittable || postJobLoading || postEndpointsLoading || open }>Submit</Button>
            </Grid>
          </CardActions>
        </Card>
      </form>
      <DLTSSnackbar message={showMessage(open,showDeleteTemplate,showSaveTemplate)}
        open={open || showSaveTemplate || showDeleteTemplate}
        style={styleSnack}
        handleWarnClose={handleClose}
        autoHideDuration={1000}
      />
    </Container>
  );
});

export default Training;
