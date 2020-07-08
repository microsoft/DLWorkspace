import * as React from 'react'
import { FunctionComponent } from 'react'

import 'typeface-roboto'
import 'typeface-roboto-mono'

import { BrowserRouter } from 'react-router-dom'
import Helmet from 'react-helmet'
import { CssBaseline, createMuiTheme } from '@material-ui/core'
import { ThemeProvider } from '@material-ui/styles'
import { SnackbarProvider } from 'notistack'
import {
  Provider as FetchProvider,
  IncomingOptions,
  CachePolicies
} from 'use-http-1'

import ConfigContext, { Provider as ConfigProvider } from './contexts/Config'
import UserContext, { Provider as UserProvider } from './contexts/User'
import { Provider as ClustersProvider } from './contexts/Clusters'
import { Provider as TeamProvider } from './contexts/Team'

import { ConfirmProvider } from './hooks/useConfirm'

import Layout from './Layout'
import Routes from './Routes'

const theme = createMuiTheme()
const useHttpOptions: IncomingOptions = {
  cachePolicy: CachePolicies.NO_CACHE
}

interface BootstrapProps {
  config: ConfigContext
  user: UserContext
}

const Contexts: FunctionComponent<BootstrapProps> = ({ config, user, children }) => {
  return (
    <FetchProvider options={useHttpOptions}>
      <BrowserRouter>

        <ConfigProvider {...config}>
          <UserProvider {...user}>
            <TeamProvider>
              <ClustersProvider>

                <ThemeProvider theme={theme}>
                  <SnackbarProvider>
                    <ConfirmProvider>
                      {children}
                    </ConfirmProvider>
                  </SnackbarProvider>
                </ThemeProvider>

              </ClustersProvider>
            </TeamProvider>
          </UserProvider>
        </ConfigProvider>

      </BrowserRouter>
    </FetchProvider>
  )
}

const App: React.FC<BootstrapProps> = (props) => (
  <Contexts {...props}>
    <Helmet
      titleTemplate="%s - Deep Learning Training Service"
      defaultTitle="Deep Learning Training Service"
    />
    <CssBaseline/>
    <Layout>
      <Routes/>
    </Layout>
  </Contexts>
)

export default App
