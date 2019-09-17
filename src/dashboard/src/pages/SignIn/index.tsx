import React from "react";

import { RouteComponentProps } from "react-router-dom"

import { Box, Grid, Paper, Typography, Button, CircularProgress } from "@material-ui/core";
import { createStyles, makeStyles } from "@material-ui/core/styles";

import image1 from "./image1.jpeg";
import image2 from "./image2.jpeg";
import image3 from "./image3.jpeg";

import UserContext from "../../contexts/User";

const useStyles = makeStyles(() => createStyles({
  container: {
    backgroundImage: `url(${[image1, image2, image3][Date.now() % 3]})`,
    backgroundSize: "cover",
    backgroundPosition: "right"
  }
}));

const SignIn: React.FC<RouteComponentProps> = ({ history }) => {
  const { email } = React.useContext(UserContext);
  const [ signIn, setSignIn ] = React.useState(false);
  const onButtonClick = React.useCallback(() => {
    setSignIn(true);
  }, []);
  React.useEffect(() => {
    if (email !== undefined) {
      history.replace('/');
    }
  }, [email, history])

  const styles = useStyles();

  return (
    <Grid container justify="flex-end" className={styles.container}>
      <Grid
        item xl={4} lg={5} md={6} sm={8} xs={12} zeroMinWidth
        container alignItems="stretch" justify="flex-end"
      >
        <Paper square elevation={6}>
          <Box paddingTop={10} paddingRight={5} paddingBottom={10} paddingLeft={5} minHeight="100%" display="flex">
            <Grid container direction="column" spacing={10} alignItems="center" justify="center">
              <Grid item>
                <Typography variant="h2" component="h1" align="center">
                  Deep Learning Training Service
                </Typography>
              </Grid>
              <Grid item>
                <Button
                  variant="outlined"
                  color="primary"
                  href="/api/authenticate"
                  disabled={signIn}
                  onClick={onButtonClick}
                >
                  { signIn ? <CircularProgress size={24}/> : 'Sign in with corp account' }
                </Button>
              </Grid>
              <Grid item>
                <Typography variant="body2">
                  {"Built with "}
                  <span role="img" aria-label="heart">❤️</span>
                  {" by ..."}
                </Typography>
              </Grid>
            </Grid>
          </Box>
        </Paper>
      </Grid>
    </Grid>
  );
};

export default SignIn;
