import * as React from 'react'
import {
  FunctionComponent,
  Suspense,
  lazy
} from 'react'

import {
  Redirect,
  Route,
  Switch
} from 'react-router-dom'

import Loading from './components/Loading'

const Home = lazy(() => import('./pages/Home'))
const Submission = lazy(() => import('./pages/Submission'))
const Jobs = lazy(() => import('./pages/Jobs'))
const JobsLegacy = lazy(() => import('./pages/JobsLegacy'))
const Job = lazy(() => import('./pages/Job'))
const JobLegacy = lazy(() => import('./pages/JobLegacy'))
const ClusterStatus = lazy( () => import('./pages/ClusterStatus'))
const Clusters = lazy(() => import('./pages/Clusters'))
const Cluster = lazy(() => import('./pages/Cluster'))
const Quota = lazy(() => import('./pages/Quota'))
const Keys = lazy(() => import('./pages/Keys'))
const AllowedIP = lazy(() => import('./pages/AllowedIP'))

const Routes: FunctionComponent = () => (
  <Suspense fallback={<Loading>Loading Your Page...</Loading>}>
    <Switch>
      <Route exact path="/" component={Home}/>

      <Route path="/submission" component={Submission}/>

      <Route strict exact path="/jobs/:clusterId/:jobId" component={Job}/>
      <Redirect strict exact from="/jobs/:clusterId" to="/jobs/:clusterId/"/>
      <Route strict exact path="/jobs/:clusterId/" component={Jobs}/>
      <Redirect strict exact from="/jobs" to="/jobs/"/>
      <Route strict exact path="/jobs/" component={Jobs}/>

      <Route path="/jobs-legacy/:cluster" component={JobsLegacy}/>
      <Route path="/jobs-legacy" component={JobsLegacy}/>
      <Route path="/job-legacy/:team/:clusterId/:jobId" component={JobLegacy}/>

      <Redirect strict exact from="/clusters" to="/clusters/"/>
      <Route strict exact path="/clusters/" component={Clusters}/>
      <Route strict exact path="/clusters/:clusterId" component={Cluster}/>
      {/* Hidden Admin-only Route */}
      <Route strict exact path="/clusters/:clusterId/quota" component={Quota}/>

      <Route path="/cluster-status" component={ClusterStatus}/>

      <Route path="/keys" component={Keys}/>
      <Route path="/allowed-ip" component={AllowedIP}/>

      {/* Backward Compatibility Routes */}
      <Route strict exact path="/jobs-v2:rest(.*)"
        render={({ match }) => <Redirect to={`/jobs${match.params['rest']}`}/>}
      />
      <Redirect path="/job/:team/:clusterId/:jobId" to="/jobs/:clusterId/:jobId"/>

      {/* 404 */}
      <Redirect to="/"/>
    </Switch>
  </Suspense>
)

export default Routes
