import * as React from 'react';
import {useState} from "react";

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
import { useHistory, useLocation } from "react-router-dom";
import IconButton from '@material-ui/core/IconButton';
import useFetch from "use-http";
import { join } from 'path';

import ClusterSelectField from "./components/ClusterSelectField";
import UserContext from "../../contexts/User";
import ClustersContext from '../../contexts/Clusters';
import TeamContext from "../../contexts/Team";
import theme, { Provider as MonospacedThemeProvider } from "../../contexts/MonospacedTheme";
import {BarChart, Bar, XAxis, YAxis, CartesianGrid, LabelList} from "recharts";
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
import * as _ from "lodash";

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
const Training: React.FunctionComponent = () => {
  const history = useHistory()
  const location = useLocation()
  const { clusters } = React.useContext(ClustersContext);
  const [ selectedCluster,saveSelectedCluster ] = React.useState(() => {
    const clusterId = location.state != null ? location.state.cluster : undefined
    if (clusters.some(({ id }) => id === clusterId)) {
      return clusterId
    }
    return clusters[0].id
  });
  const { email } = React.useContext(UserContext);
  const { currentTeamId }= React.useContext(TeamContext);
  //const team = 'platform';
  const [showGPUFragmentation, setShowGPUFragmentation] = React.useState(false)
  const [grafanaUrl, setGrafanaUrl] = React.useState('');
  const [name, setName] = React.useState("");
  const [gpuFragmentation, setGpuFragmentation] = React.useState<any[]>([]);
  const onNameChange = React.useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      setName(event.target.value);
    },
    [setName]
  );
  const cluster = React.useMemo(() => {
    if (selectedCluster == null) return;
    return clusters.filter((cluster: any) => cluster.id === selectedCluster)[0];
  }, [clusters, selectedCluster]);
  const gpuModel = React.useMemo(() => {
    if (cluster == null) return;
    return Object.keys(cluster.gpus)[0];
  }, [cluster]);
  const gpusPerNode = React.useMemo(() => {
    if (cluster == null || gpuModel == null) return;
    return cluster.gpus[gpuModel].perNode;
  }, [cluster, gpuModel]);

  const {
    data: templates,
    get: getTemplates,
  } = useFetch('/api');
  React.useEffect(() => {
    getTemplates(`/teams/${currentTeamId}/templates`);
  }, [currentTeamId]);

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
  const [accountName, setAccountName] = React.useState("");
  const [accountKey, setAccountKey] = React.useState("");
  const [containerName, setContainerName] = React.useState("");
  const [mountPath, setMountPath] = React.useState("");
  const [mountOptions, setMountOptions] = React.useState("");
  const onAccountNameChange = React.useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      setAccountName(event.target.value);
    },
    [setAccountName]
  )
  const onAccountKeyChange = React.useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      setAccountKey(event.target.value);
    },
    [setAccountKey]
  )
  const onContainerNameChange = React.useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      setContainerName(event.target.value);
    },
    [setContainerName]
  )
  const onMountPathChange = React.useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      setMountPath(event.target.value);
    },
    [setMountPath]
  )
  const onMountOptionsChange = React.useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      setMountOptions(event.target.value);
    },
    [setMountOptions]
  )
  const [workPath, setWorkPath] = React.useState("");
  const onWorkPathChange = React.useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      setWorkPath(event.target.value);
    },
    [setWorkPath]
  )
  const [dockerRegistry, setDockerRegistry] = React.useState("");
  const [dockerUsername, setDockerUsername] = React.useState("");
  const [dockerPassword, setDockerPassword] = React.useState("");
  const onDockerRegistryChange = React.useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      setDockerRegistry(event.target.value)
    },
    [setDockerRegistry]
  )
  const onDockerUsernameChange = React.useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      setDockerUsername(event.target.value)
    },
    [setDockerUsername]
  )
  const onDockerPasswordChange = React.useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      setDockerPassword(event.target.value)
    },
    [setDockerPassword]
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

  const [maxRetryCount, setMaxRetryCount] = React.useState(3);
  const onMaxRetryCountChange = React.useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      let value = event.target.valueAsNumber || 0;
      if (value < 0) { value = 0; }
      setMaxRetryCount(value);
    },
    [setMaxRetryCount]
  )

  const [database, setDatabase] = React.useState(false);
  // const onDatabaseClick = React.useCallback(() => {
  //   setDatabase(true);
  // }, []);
  const onTemplateClick = () => {
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
  const {
    put: saveTemplate,
    delete: deleteTemplate,
  } = useFetch('/api');
  const [gpus, setGpus] = React.useState(0);
  const submittable = React.useMemo(() => {
    if (!gpuModel) return false;
    if (!currentTeamId) return false;
    if (!name) return false;
    if (!image) return false;
    if (!command.trim()) return false;
    if (type === 'RegularJob' && gpus > gpusPerNode) return false;
    if (/^\d+$/.test(name)) return false;

    return true;
  }, [gpuModel, currentTeamId, name, image, command, type, gpus, gpusPerNode]);
  const onSaveTemplateClick = async () => {
    try {
      let plugins: any = {};
      plugins['blobfuse'] = [];

      let blobfuseObj: any = {};
      blobfuseObj['accountName'] = accountName || '';
      blobfuseObj['accountKey'] = accountKey || '';
      blobfuseObj['containerName'] = containerName || '';
      blobfuseObj['mountPath'] = mountPath || '';
      blobfuseObj['mountOptions'] = mountOptions || '';
      plugins['blobfuse'].push(blobfuseObj);

      plugins['imagePull'] = [];
      let imagePullObj: any = {};
      imagePullObj['registry'] = dockerRegistry
      imagePullObj['username'] = dockerUsername
      imagePullObj['password'] = dockerPassword
      plugins['imagePull'].push(imagePullObj)

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
        plugins
      };
      const url = `/teams/${currentTeamId}/templates/${saveTemplateName}?database=${saveTemplateDatabase}`;
      await saveTemplate(url, template);
      setSaveTemplate(true)
      window.location.reload()
    } catch (error) {
      alert('Failed to save the template, check console (F12) for technical details.')
      console.error(error);
    }
  };
  const [showDeleteTemplate, setShowDeleteTemplate] = useState(false)
  const onDeleteTemplateClick = async () => {
    try {
      let plugins: any = {};
      plugins['blobfuse'] = [];
      let blobfuseObj: any = {};
      blobfuseObj['accountName'] = accountName || '';
      blobfuseObj['accountKey'] = accountKey || '';
      blobfuseObj['containerName'] = containerName || '';
      blobfuseObj['mountPath'] = mountPath || '';
      plugins['blobfuse'].push(blobfuseObj);
      plugins['imagePull'] = [];
      let imagePullObj: any = {};
      imagePullObj['registry'] = dockerRegistry
      imagePullObj['username'] = dockerUsername
      imagePullObj['password'] = dockerPassword
      plugins['imagePull'].push(imagePullObj)
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
        plugins,
      };
      const url = `/teams/${currentTeamId}/templates/${saveTemplateName}?database=${saveTemplateDatabase}`;
      await deleteTemplate(url);
      setShowDeleteTemplate(true)
      window.location.reload()
    } catch (error) {
      alert('Failed to delete the template, check console (F12) for technical details.')
      console.error(error);
    }
  }
  const [json, setJson] = React.useState('-1');
  const onTemplateChange = React.useCallback(
    (event: React.ChangeEvent<{ value: unknown }>) => {
      setJson(event.target.value as string)
      if (event.target.value === '-1') {
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
          plugins
        } = JSON.parse(event.target.value as string);
        if (name !== undefined) setName(currentName => currentName !== '' ? currentName : name);
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
        if (plugins === undefined) {
          setAccountName("");
          setAccountKey("");
          setContainerName("");
          setMountPath("");
          setMountOptions("");
          setDockerRegistry("")
          setDockerUsername("")
          setDockerPassword("")
        }
        if (plugins !== undefined) {
          if (plugins.hasOwnProperty("blobfuse") && Array.isArray(plugins['blobfuse'])) {
            let blobfuseObj = plugins['blobfuse'][0];
            setAccountName(blobfuseObj['accountName']);
            setAccountKey(blobfuseObj['accountKey']);
            setContainerName(blobfuseObj['containerName']);
            setMountPath(blobfuseObj['mountPath']);
            setMountOptions(blobfuseObj['mountOptions']);
          }

          if (plugins.hasOwnProperty('imagePull') && Array.isArray(plugins['imagePull'])) {
            let imagePullObj = plugins['imagePull'][0];
            setDockerRegistry(imagePullObj['registry'])
            setDockerUsername(imagePullObj['username'])
            setDockerPassword(imagePullObj['password'])
          }
        }
      }
    },
    []
  );

  const {
    data: postJobData,
    loading: postJobLoading,
    error: postJobError,
    post: postJob,
  } = useFetch('/api');
  const {
    data: postEndpointsData,
    loading: postEndpointsLoading,
    error: postEndpointsError,
    post: postEndpoints,
  } = useFetch('/api');



  const [enableSubmit, setEnableSubmit] = React.useState(submittable);

  const onGpusChange = React.useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      let value = event.target.valueAsNumber || 0;
      if (value < 0) { value = 0; }
      if (value > 0) { value = 26; }
      setGpus(event.target.valueAsNumber);
      setEnableSubmit(false)
      if (type === 'RegularJob' && event.target.valueAsNumber > gpusPerNode)  {
        setEnableSubmit(true);
      }
    },
    [gpusPerNode, type]
  );
  const [open, setOpen] = React.useState(false);
  const onSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    if (!submittable) return;
    let plugins: any = {};
    plugins['blobfuse'] = [];
    let blobfuseObj: any = {};
    blobfuseObj['accountName'] = accountName || '';
    blobfuseObj['accountKey'] = accountKey || '';
    blobfuseObj['containerName'] = containerName || '';
    blobfuseObj['mountPath'] = mountPath || '';
    blobfuseObj['mountOptions'] = mountOptions || '';
    plugins['blobfuse'].push(blobfuseObj);
    plugins['imagePull'] = [];
    let imagePullObj: any = {};
    imagePullObj['registry'] = dockerRegistry
    imagePullObj['username'] = dockerUsername
    imagePullObj['password'] = dockerPassword
    plugins['imagePull'].push(imagePullObj)
    const job: any = {
      userName: email,
      jobType: 'training',
      gpuType: gpuModel,
      vcName: currentTeamId,
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
      envs: environmentVariables,
      hostNetwork : type === 'PSDistJob',
      isPrivileged : type === 'PSDistJob',
      plugins: plugins,
      'max_retry_count': String(maxRetryCount),
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
      history.push(`/job/${currentTeamId}/${selectedCluster}/${jobId.current}`);
    }
  }, [postJobData, ssh, ipython, tensorboard, interactivePorts, history, selectedCluster, postEndpoints, currentTeamId])
  const request = useFetch('/api/clusters')
  const fetchConfig = async () => {
    if (typeof selectedCluster !== 'string') return
    const { grafana, preemptableJobByDefault = false } = await request.get(`/${selectedCluster}`)
    setGrafanaUrl(grafana)
    setPreemptible(preemptableJobByDefault)
  }
  const handleCloseGPUGramentation = () => {
    setShowGPUFragmentation(false);
  }

  React.useEffect(() => {
    fetchConfig()
    if (postEndpointsData) {
      setOpen(true);
      setTimeout(()=>{
        history.push(`/job/${currentTeamId}/${selectedCluster}/${jobId.current}`);
      }, 2000)

    }
  }, [history, postEndpointsData, selectedCluster, currentTeamId])

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
    if (!grafanaUrl) return;
    let getNodeGpuAva = `${grafanaUrl}/api/datasources/proxy/1/api/v1/query?`;
    const params = new URLSearchParams({
      query:'count_values("gpu_available", k8s_node_gpu_available)'
    });
    fetch(getNodeGpuAva+params).then(async (res: any) => {
      const {data} = await res.json();
      const result = data['result'];
      const sortededResult = result.sort((a: any, b: any)=>a['metric']['gpu_available'] - b['metric']['gpu_available']);
      setGpuFragmentation(sortededResult)
    })
  }, [grafanaUrl])

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
  const renderCustomizedLabel = (props: any) => {
    const { x, y, width, height, value } = props;
    const radius = 10;

    return (
      <g>
        <circle cx={x + width / 2} cy={y - radius} r={radius} fill="#fff" />
        <text x={x + width / 2} y={y - radius} fill="#000" textAnchor="middle" dominantBaseline="middle">
          {value}
        </text>
      </g>
    );
  };
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
        <BarChart width={500} height={700} data={gpuFragmentation}  margin={{top: 20}}>
          <CartesianGrid strokeDasharray="10 10"/>
          <XAxis dataKey={"metric['gpu_available']"} label={{value: 'Available gpu count', offset:0,position:'insideBottom'}}>
          </XAxis>
          <YAxis label={{value: 'Node count', angle: -90, position: 'insideLeft'}} />
          <Bar dataKey="value[1]" fill="#8884d8" >
            <LabelList dataKey="value[1]" content={renderCustomizedLabel} />
          </Bar>
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
                  error={/^\d+$/.test(name)}
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
                  <MenuItem value="-1" divider>None (Apply a Template)</MenuItem>
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
                  disabled={json!=='-1'}
                  onChange={onTypeChange}
                >
                  <MenuItem value="RegularJob">Regular Job</MenuItem>
                  <MenuItem value="PSDistJob">Distributed Job</MenuItem>
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
                  error={!image}
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
              <Typography component="div" variant="h6" >Azure Blob</Typography>
              <Grid
                container
                wrap="wrap"
                spacing={1}
              >
                <Grid item xs={12}>
                  <TextField
                    value={accountName}
                    onChange={onAccountNameChange}
                    label="Account Name"
                    fullWidth
                    variant="filled"
                  />
                </Grid>
                <Grid item xs={12}>
                  <TextField
                    value={accountKey}
                    onChange={onAccountKeyChange}
                    label="Account Key"
                    fullWidth
                    variant="filled"
                  />
                </Grid>
                <Grid item xs={12}>
                  <TextField
                    value={containerName}
                    onChange={onContainerNameChange}
                    label="Container Name"
                    fullWidth
                    variant="filled"
                  />
                </Grid>
                <Grid item xs={12}>
                  <TextField
                    value={mountPath}
                    onChange={onMountPathChange}
                    label="Mount Path"
                    fullWidth
                    variant="filled"
                  />
                </Grid>
                <Grid item xs={12}>
                  <TextField
                    value={mountOptions}
                    onChange={onMountOptionsChange}
                    label="Mount Options"
                    fullWidth
                    variant="filled"
                  />
                </Grid>
              </Grid>
            </CardContent>
            <CardContent>
              <Typography component="div" variant="h6" >Custom Docker Registry</Typography>
              <Grid
                container
                wrap="wrap"
                spacing={1}
              >
                <Grid item xs={12}>
                  <TextField
                    value={dockerRegistry}
                    onChange={onDockerRegistryChange}
                    label="Registry"
                    fullWidth
                    variant="filled"
                  />
                </Grid>
                <Grid item xs={12}>
                  <TextField
                    value={dockerUsername}
                    onChange={onDockerUsernameChange}
                    label="Username"
                    fullWidth
                    variant="filled"
                  />
                </Grid>
                <Grid item xs={12}>
                  <TextField
                    value={dockerPassword}
                    onChange={onDockerPasswordChange}
                    label="Password"
                    fullWidth
                    variant="filled"
                  />
                </Grid>
              </Grid>
            </CardContent>
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
                        checked={enableJobPath}
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
            <CardContent>
              <Typography component="div" variant="h6">Retry Policy</Typography>
              <Grid container wrap="wrap" spacing={1}>
                <Grid item xs={12}>
                  <TextField
                    type="number"
                    error={maxRetryCount < 0}
                    label="Max Retry Count"
                    fullWidth
                    variant="filled"
                    inputProps={{ min: 0 }}
                    value={maxRetryCount}
                    onChange={onMaxRetryCountChange}
                  />
                </Grid>
              </Grid>
            </CardContent>
          </Collapse>
          <Collapse in={database}>
            <Divider/>
            <CardContent>
              <Typography component="span" variant="h6">Template Management</Typography>
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
                    label="Scope"
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
                <Button type="button" color="secondary"  onClick={onTemplateClick}>Template</Button>
              </Grid>
              <Button type="submit" color="primary" variant="contained" disabled={!submittable || enableSubmit || postJobLoading || postEndpointsLoading || open }>Submit</Button>
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
};

export default Training;
