import * as React from 'react'
import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import useFetch from 'use-http'
import Table from '@material-ui/core/Table'
import TableBody from '@material-ui/core/TableBody'
import TableCell from '@material-ui/core/TableCell'
import TableRow from '@material-ui/core/TableRow'
import LinearProgress from '@material-ui/core/LinearProgress'
import {
  Box,
  Button,
  Card,
  CardActions,
  CardContent,
  CardHeader, createMuiTheme,
  Divider,
  IconButton,
  InputAdornment,
  Menu,
  MenuItem, MuiThemeProvider,
  TextField,
  Tooltip, Typography, withStyles
} from '@material-ui/core'
import {
  makeStyles,
  createStyles,
  useTheme,
  Theme,
  lighten
} from '@material-ui/core/styles'
import { MoreVert, FileCopyRounded } from '@material-ui/icons'

import { Cell, PieChart, Pie, ResponsiveContainer, Sector } from 'recharts'
import UserContext from '../../../contexts/User'
import TeamContext from '../../../contexts/Team'
import {
  green,
  lightGreen,
  deepOrange,
  red,
  yellow
} from '@material-ui/core/colors'
import copy from 'clipboard-copy'
import { checkObjIsEmpty, sumValues } from '../../../utlities/ObjUtlities'
import { DLTSSnackbar } from '../../CommonComponents/DLTSSnackbar'

import * as _ from 'lodash'

const useStyles = makeStyles((theme: Theme) => createStyles({
  avatar: {
    backgroundColor: theme.palette.secondary.main
  },
  cardHeaderContent: {
    width: 0
  },
  textField: {
    marginLeft: theme.spacing(1),
    marginRight: theme.spacing(1)
  },
  chart: {
    padding: 3,
    backgroundColor: theme.palette.background.default
  },
  dialogText: {
    color: green[400]
  },
  success: {
    backgroundColor: green[600]
  },
  container: {
    margin: '0 auto'
  },
  tableTitle: {
    display: 'flex',
    justifyContent: 'center'
  },
  tableInfo: {
    justifyContent: 'space-between',
    display: 'flex'
  }
}))

const ActionIconButton: React.FC<{cluster?: string}> = ({ cluster }) => {
  const [open, setOpen] = React.useState(false)
  const iconButton = React.useRef<any>()
  const onIconButtonClick = React.useCallback(() => setOpen(true), [setOpen])
  const onMenuClose = React.useCallback(() => setOpen(false), [setOpen])

  return (
    <>
      <IconButton ref={iconButton} onClick={onIconButtonClick}>
        <MoreVert/>
      </IconButton>
      <Menu
        anchorEl={iconButton.current}
        anchorOrigin={{ horizontal: 'right', vertical: 'top' }}
        transformOrigin={{ horizontal: 'right', vertical: 'top' }}
        open={open}
        onClose={onMenuClose}
      >
        <MenuItem component={Link} to={'/cluster-status'}>Cluster Status</MenuItem>
        <MenuItem component={Link} to={`/jobs/${cluster}`}>View Jobs</MenuItem>
      </Menu>
    </>
  )
}

const Chart: React.FC<{
  available: number
  used: number
  reserved: number
  isActive: boolean

}> = ({ available, used, reserved, isActive }) => {
  const theme = useTheme()
  let data = [
    { name: 'Available', value: available, color: lightGreen[400] },
    { name: 'Used', value: used, color: theme.palette.grey[500] },
    { name: 'Unschedulable', value: reserved, color: deepOrange[400] }
  ]
  if (reserved === 0) {
    data = data.filter((item) => item.name !== 'Reserved')
  }
  const renderActiveShape = (props: any) => {
    const RADIAN = Math.PI / 180
    const {
      cx, cy, midAngle, innerRadius, outerRadius, startAngle, endAngle,
      fill, payload, percent, value
    } = props
    const sin = Math.sin(-RADIAN * midAngle)
    const cos = Math.cos(-RADIAN * midAngle)
    const mx = cx + (outerRadius + 20) * cos
    const my = cy + (outerRadius + 20) * sin
    const ex = mx + (cos >= 0 ? 1 : -1) * 8
    const ey = my
    const textAnchor = cos >= 0 ? 'start' : 'end'

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
        <text x={ex + (cos >= 0 ? 1 : -1) * 12} y={ey} textAnchor={textAnchor} fill="#333">{`${value}`}</text>
        <text x={ex + (cos >= 0 ? 1 : -1) * 12} y={ey} dy={18} textAnchor={textAnchor} fill="#999">
          {`(${(Math.round(percent * 100))}%)`}
        </text>
      </g>
    )
  }
  const [activeIndex, setActiveIndex] = useState(0)
  const onPieEnter = (data: any, index: number) => {
    setActiveIndex(index)
  }
  return (
    <>
      <ResponsiveContainer aspect={8 / 8} width='100%' height='100%'>
        <PieChart>
          <Pie
            dataKey="value"
            isAnimationActive={isActive}
            activeIndex={activeIndex}
            activeShape={renderActiveShape}
            data={data}
            cx={170}
            cy={165}
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
  label: string
  value: string
}> = ({ label, value }) => {
  const input = React.useRef<HTMLInputElement>(null)
  const [openCopyWarn, setOpenCopyWarn] = React.useState(false)
  const handleWarnClose = () => {
    setOpenCopyWarn(false)
  }
  const onMouseOver = React.useCallback(() => {
    if (input.current) {
      input.current.select()
    }
  }, [input])
  const onFocus = React.useCallback(() => {
    if (input.current) {
      input.current.select()
    }
  },
  [input])
  const handleCopy = React.useCallback(() => {
    if (input.current) {
      copy(input.current.innerHTML).then(() => {
        setOpenCopyWarn(true)
      })
    }
  }, [input])
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
      <DLTSSnackbar message={'Successfully copied'} autoHideDuration={500} open={openCopyWarn} handleWarnClose={handleWarnClose} />
    </>
  )
}

const ClusterCard: React.FC<{ clusterId: string }> = ({ clusterId }) => {
  const styles = useStyles()
  const [activeJobs, setActiveJobs] = useState(0)
  const [available, setAvailable] = useState(0)
  const [used, setUsed] = useState(0)
  const [reversed, setReserved] = useState(0)
  const [workStorage, setWorkStorage] = useState('')
  const [dataStorage, setDataStorage] = useState('')
  const [activate, setActivate] = useState(false)
  const { email } = React.useContext(UserContext)
  const { currentTeamId } = React.useContext(TeamContext)
  const fetchDiretoryUrl = `api/clusters/${clusterId}`
  const request = useFetch(fetchDiretoryUrl)
  const fetchDirectories = async () => {
    const data = await request.get('')
    const name = typeof email === 'string' ? email.split('@', 1)[0] : email
    setDataStorage(data.dataStorage)
    setWorkStorage(`${data.workStorage}/${name}`)
    return data
  }
  const fetchClusterStatusUrl = '/api'
  const requestClusterStatus = useFetch(fetchClusterStatusUrl)
  const fetchClusterStatus = async () => {
    setActivate(false)
    const data = await requestClusterStatus.get(`/teams/${currentTeamId}/clusters/${clusterId}`)
    return data
  }
  const [nfsStorage, setNfsStorage] = useState([])
  useEffect(() => {
    fetchDirectories().then((res) => {
      const fetchStorage = []
      const availBytesSubPath = '/api/datasources/proxy/1/api/v1/query?query=node_filesystem_avail_bytes%7Bfstype%3D%27nfs4%27%7D'
      const sizeBytesSubPath = '/api/datasources/proxy/1/api/v1/query?query=node_filesystem_size_bytes%7Bfstype%3D%27nfs4%27%7D'
      fetchStorage.push(fetch(`${res['grafana']}${availBytesSubPath}`))
      fetchStorage.push(fetch(`${res['grafana']}${sizeBytesSubPath}`))
      let storageRes: any = []
      const tmpStorage: any = []
      Promise.all(fetchStorage).then((responses) => {
        const processPromise = async (response: any) => {
          const res = await response.json()
          if (res['data']) {
            for (const item of res['data']['result']) {
              const tmp = {} as any
              if (item['metric']['__name__'] === 'node_filesystem_size_bytes') {
                const mountpointName = item['metric']['mountpoint']
                const val = Math.floor(item['value'][1] / (Math.pow(10, 9)))
                tmp['mountpointName'] = mountpointName
                tmp['total'] = val
              }
              const tmpAvail = {} as any
              // node_filesystem_avail_bytes
              if (item['metric']['__name__'] === 'node_filesystem_avail_bytes') {
                const mountpointName = item['metric']['mountpoint']
                const val = Math.floor(item['value'][1] / (Math.pow(10, 9)))
                tmpAvail['mountpointName'] = mountpointName
                tmpAvail['Avail'] = val
              }
              tmpStorage.push(tmp)
              tmpStorage.push(tmpAvail)
            }
          }
          // ({ mountpointName: key, users: value })
          storageRes = tmpStorage.filter((store: any) => !checkObjIsEmpty(store))
          let finalStorageRes: any = []
          if (storageRes && storageRes.length > 0) {
            finalStorageRes = _.chain(storageRes).groupBy('mountpointName').map((value, key) => {
              const tmpTotal: any = value.filter((item: any) => 'total' in item)
              const tmpAvail: any = value.filter((item: any) => 'Avail' in item)
              let total = 0
              let used = 0
              if (typeof tmpTotal[0] !== 'undefined' && typeof tmpAvail[0] !== 'undefined') {
                total = tmpTotal[0]['total']
                used = tmpTotal[0]['total'] - tmpAvail[0]['Avail']
              }
              return {
                mountpointName: key, total: total, used: used
              }
            }).value()
          }
          finalStorageRes.forEach((item: any, i: number) => {
            if (item['mountpointName'].indexOf('dlws/nfs') !== -1) {
              finalStorageRes.splice(i, 1)
              finalStorageRes.unshift(item)
            }
          })
          finalStorageRes = finalStorageRes.filter((item: any) => {
            return !(item['mountpointName'].indexOf('dlts') === -1 && item['mountpointName'].indexOf('dlws/nfs') === -1)
          })
          setNfsStorage(finalStorageRes.filter((store: any) => {
            if (currentTeamId === 'MMBellevue' && store['mountpointName'].indexOf('/mntdlws/nfs') !== -1) {
              return null
            }
            return store['mountpointName'].indexOf(currentTeamId) !== -1 || store['mountpointName'].indexOf('dlws/nfs') !== -1
          }))
        }
        responses.forEach((response) => {
          processPromise(response)
        })
      })
    })
    fetchClusterStatus().then((res) => {
      const availableGpu = !checkObjIsEmpty(res['gpu_avaliable']) ? (Number)(sumValues(res['gpu_avaliable'])) : 0
      setAvailable(availableGpu)
      const usedGpu = !checkObjIsEmpty(res['gpu_used']) ? (Number)(sumValues(res['gpu_used'])) : 0
      setUsed(usedGpu)
      const reversedGpu = !checkObjIsEmpty(res['gpu_unschedulable']) ? (Number)(sumValues(res['gpu_unschedulable'])) : 0
      setReserved(reversedGpu)
      setActiveJobs((Number)(sumValues(res['AvaliableJobNum'])))
      setActivate(true)
    })
  }, [currentTeamId]) // eslint-disable-line react-hooks/exhaustive-deps
  const tableTheme = createMuiTheme({
    overrides: {
      MuiTableCell: {
        root: {
          paddingTop: 10,
          paddingBottom: 10,
          paddingLeft: 2,
          paddingRight: 5
        }
      }
    }
  })
  const BorderLinearProgress = withStyles({
    root: {
      height: 10,
      backgroundColor: lighten('#363636', 0.5)
    },
    bar: {
      borderRadius: 20,
      backgroundColor: green[400]
    }
  })(LinearProgress)
  const GenernalLinerProgress = withStyles({
    root: {
      height: 10,
      backgroundColor: lighten('#363636', 0.5)
    },
    bar: {
      borderRadius: 20,
      backgroundColor: yellow[800]
    }
  })(LinearProgress)
  const FullBorderLinearProgress = withStyles({
    root: {
      height: 10,
      backgroundColor: lighten('#363636', 0.5)
    },
    bar: {
      borderRadius: 20,
      backgroundColor: red[400]
    }
  })(LinearProgress)

  const processedNfsStorage = useMemo(() => {
    return _.chain(nfsStorage).map((nfs: any) => {
      const {
        mountpointName,
        total,
        used
      } = nfs
      let processedMountpointName = '/data'
      let order = 1
      if (mountpointName.indexOf('/mntdlws') === -1) {
        processedMountpointName = mountpointName.slice(mountpointName.lastIndexOf('/'))
        order = 0
      }
      return {
        mountpointName: processedMountpointName,
        total,
        used,
        order
      }
    }).uniqBy('mountpointName').sortBy(['order', 'mountpointName']).value()
  }, [nfsStorage])

  return (
    <Card>
      <CardHeader
        title={clusterId}
        titleTypographyProps={{
          component: 'h3',
          variant: 'body2',
          noWrap: true
        }}
        subheader={` ${activeJobs} Active Jobs`}
        action={<ActionIconButton cluster={clusterId}/>}
        classes={{ content: styles.cardHeaderContent }}
      />
      <CardContent className={styles.chart}>
        <Chart available={available} used={used} reserved={reversed} isActive={activate} />
        <Divider />
        <Typography variant="h6" id="tableTitle" className={styles.tableTitle}>
          {'Storage (GB)'}
        </Typography>
        <Box height={102} style={{ overflow: 'auto' }}>
          <MuiThemeProvider theme={tableTheme}>
            <Table>
              <TableBody>
                {
                  processedNfsStorage.map((nfs: any) => {
                    const mounName = nfs['mountpointName']
                    const value = nfs['total'] === 0 ? 0 : (nfs['used'] / nfs['total']) * 100
                    return (
                      <TableRow key={mounName}>
                        <TableCell>
                          {
                            value < 80 ? <BorderLinearProgress value={value} variant={'determinate'}/> : value >= 80 && value < 90 ? <GenernalLinerProgress value={value} variant={'determinate'}/> : <FullBorderLinearProgress value={value} variant={'determinate'}/>
                          }
                          <div className={styles.tableInfo}><span>{`${mounName}`}</span><span>{`(${nfs['used']}/${nfs['total']}) ${Math.floor(value)}% used`}</span></div>
                        </TableCell>
                      </TableRow>
                    )
                  })
                }
              </TableBody>
            </Table>
          </MuiThemeProvider>
        </Box>
      </CardContent>
      <CardActions>
        <Button component={Link}
          to={{ pathname: '/submission/training-cluster', state: { cluster: clusterId } }}
          size="small" color="secondary"
        >
          Submit Training Job
        </Button>
        <Button component={Link}
          to={{ pathname: '/submission/data', state: { cluster: clusterId } }}
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
  )
}

export default ClusterCard
