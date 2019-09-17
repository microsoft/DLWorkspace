import React from "react";

import { Redirect, Route, Switch, withRouter } from "react-router-dom";

import Training from "./Training";
import DataJob  from "./DataJob";

const Submit = withRouter(({ match }) => {
  return (
    <Switch>
      <Route exact path={`${match.path}/training`} component={Training}/>
      <Route exact path={`${match.path}/training-cluster`} component={Training}/>
      <Route exact path={`${match.path}/data`} component={DataJob}/>
      <Redirect to="/"/>
    </Switch>
  );
});

export default Submit;
