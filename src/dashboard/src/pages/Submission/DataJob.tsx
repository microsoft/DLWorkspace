import * as React from 'react';
import {useEffect, useState} from "react";
import { TransitionProps } from '@material-ui/core/transitions';
import {
  Card,
  CardHeader,
  CardContent,
  CardActions,
  Grid,
  Container,
  TextField,
  Button,
  Divider, Dialog, DialogTitle, DialogContent, DialogContentText, DialogActions,
} from "@material-ui/core";
import { makeStyles, createStyles } from "@material-ui/core/styles";
import ClusterSelectField from "./components/ClusterSelectField";
import { DirectoryPathTextField } from './components/GPUCard'
import ClustersContext from "../../contexts/Clusters";
import UserContext from "../../contexts/User";
import TeamContext from "../../contexts/Team";
import {Link} from "react-router-dom";
import Slide from "@material-ui/core/Slide";
import {green} from "@material-ui/core/colors";
import useFetch from "use-http";
import formats from '../../Configuration/foldFormat.json';
const useStyles = makeStyles(() =>
  createStyles({
    container: {
      margin: "auto"
    },
    submitButton: {
      marginLeft: "auto"
    },
    dialogText: {
      color:green[400]
    }
  })
);

const Transition = React.forwardRef<unknown, TransitionProps & { children?: React.ReactElement }>(function Transition(props, ref) {
  return <Slide direction="down" ref={ref} {...props} />;
});

const DataJob: React.FC = (props: any) => {
  const styles = useStyles();
  const [azureDataStorage, setAzureDataStorage] = useState('');
  const [nfsDataStorage, setNFSDataStorage] = useState('');
  const [openDialog, setOpenDialog] = useState(false);
  const[dialogContentText, setDialogContentText] = useState('');
  const [submittable, setSubmittable] = useState(true);
  const {email} = React.useContext(UserContext);
  const {currentTeamId} = React.useContext(TeamContext);
  const {clusters} = React.useContext(ClustersContext);
  const [ selectedCluster,saveSelectedCluster ] = React.useState(() => clusters[0].id);
  const [workStorage, setWorkStorage ] = useState('');
  const [dataStorage, setDataStorage] = useState('');

  const cluster = React.useMemo(() => {
    if (selectedCluster == null) return;
    return clusters.filter((cluster: any) => cluster.id === selectedCluster)[0];
  }, [clusters, selectedCluster]);
  const gpuModel = React.useMemo(() => {
    if (cluster == null) return;
    return Object.keys(cluster.gpus)[0];
  }, [cluster]);

  const handleClose = () => {
    setOpenDialog(false);
  }
  const fetchDiretoryUrl = `/api/clusters/${selectedCluster}`;
  const request = useFetch(fetchDiretoryUrl);
  const fetchStorage = async () => {
    const data = await request.get('/');
    const name = typeof email === 'string' ?  email.split('@', 1)[0] : email;
    setDataStorage(data.dataStorage);
    setWorkStorage(`${data.workStorage}/${name}`);
  }
  useEffect(()=>{
    const { cluster } = props.location.state || '';
    if (cluster) {saveSelectedCluster(cluster)}
    fetchStorage();
  },[selectedCluster, props.location.state, email, saveSelectedCluster])

  const handleChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.name === 'azureDataStorage') {
      setAzureDataStorage(event.target.value);
    }
    if (event.target.name === 'nfsDataStorage') {
      setNFSDataStorage(event.target.value);
    }
    if ((nfsDataStorage.length > 0 && azureDataStorage.length > 0) || event.target.value.length > 0) {
      setSubmittable(false)
    } else {
      setSubmittable(true)
    }

  }

  const convertURI = (type: string, folder: string) => {
    if (type === "adls") {
      if (folder.match(/^adl:\/\//)) {
        // adl://example.com/file
        return folder;
      } else if (folder.match(/^\/\//i)) {
        // //example.com/file
        return "adl:" + folder;
      } else if (folder.match(/^\//i)) {
        // /example.com/file
        return "adl:/" + folder;
      } else {
        // example.com/file
        return "adl://" + folder;
      }
    } else if (type === "nfs") {
      if (folder.match(/^\//)) {
        // /dir/file
        return folder;
      } else {
        // dir/file
        return "/" + folder;
      }
    }
    return folder;
  }
  const covert = (dataJob: any) => {
    dataJob.vcName = currentTeamId;
    dataJob.jobName = "Data Job @ " + new Date().toISOString();
    if (azureDataStorage) {dataJob.fromFolder = azureDataStorage;}
    if (nfsDataStorage) {dataJob.toFolder = nfsDataStorage;}
    dataJob.userName = email;
    dataJob.jobType = 'training';
    dataJob.jobtrainingtype = "RegularJob";
    dataJob.gpuType = gpuModel;
    dataJob.runningasroot = "1";
    dataJob.resourcegpu = 0;
    dataJob.containerUserId = 0;
    dataJob.image = "indexserveregistry.azurecr.io/dlts-data-transfer-image";
    dataJob.cmd = [
      "cd /DataUtils && ./copy_data.sh",
      convertURI("adls", dataJob.fromFolder),
      convertURI("nfs", dataJob.toFolder),
      "False 33554432 4 8"
    ].join(" ");
    return dataJob;
  }
  const[currentJobId, setCurrentJobId] = useState('');
  const postDataJob = () => {
    let dataJob: any = {};
    dataJob = covert(dataJob);
    fetch(`/api/clusters/${selectedCluster}/jobs`,{
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body:JSON.stringify(dataJob)
    }).then(async (res: any) => {
      const data = await res.json();
      const { jobId } = data;
      if (jobId) {
        setDialogContentText(`${jobId} successfully submitted`);
        setCurrentJobId(jobId);
        setOpenDialog(true);
      }
    })
  }

  return (
    <Container maxWidth="md" className={styles.container}>
      <Card>
        <CardHeader title="Manage Data"/>
        <Divider/>
        <CardContent>
          <Grid
            container
            wrap="wrap"
            spacing={1}
          >
            <Grid item xs={12} sm={6}>
              <ClusterSelectField
                fullWidth
                cluster={selectedCluster}
                onClusterChange={saveSelectedCluster}
              />
            </Grid>
            <DirectoryPathTextField
              label="Work Directory"
              value={workStorage}
            />
            <DirectoryPathTextField
              label="Data Directory"
              value={dataStorage}
            />
            <TextField
              error={ !azureDataStorage}
              name={"azureDataStorage"}
              onChange={handleChange}
              id="outlined-error"
              label="From Folder of Azure Data Lake Storage *"
              defaultValue={formats.azureDataStorage}
              placeholder={formats.azureDataStorage}
              fullWidth
              margin="dense"
            />
            <TextField
              error={!nfsDataStorage}
              name={"nfsDataStorage"}
              onChange={handleChange}
              id="outlined-error"
              defaultValue={formats.nfsDataStorage}
              placeholder={formats.nfsDataStorage}
              label="To NFS Data Folder *"
              fullWidth
              margin="dense"
            />
          </Grid>
        </CardContent>
        <CardActions>
          <Button type="submit"  disabled ={submittable} color="primary" variant="contained" className={styles.submitButton}  onClick={postDataJob}>Submit</Button>
        </CardActions>
      </Card>
      <Dialog
        open={openDialog}
        TransitionComponent={Transition}
        onClose={handleClose}
        aria-labelledby="alert-dialog-title"
        aria-describedby="alert-dialog-description"
      >
        <DialogTitle id="alert-dialog-title">{"Info"}</DialogTitle>
        <DialogContent>
          <DialogContentText id="alert-dialog-description" className={styles.dialogText}>
            { dialogContentText }
          </DialogContentText>
          <DialogActions>
            <Button component={Link}
              to={ `/job/${currentTeamId}/${selectedCluster}/${currentJobId}` }
              color="secondary"
            >
                  ok
            </Button>
          </DialogActions>
        </DialogContent>
      </Dialog>
    </Container>
  )
}

export default DataJob;
