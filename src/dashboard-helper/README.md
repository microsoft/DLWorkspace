# Dashboard Helper

Web extension for DLTS dashboard.

## Features

- Mock the current user with any user.

## Prerequisites

- [Node.js](https://nodejs.org/)
- [Yarn](https://yarnpkg.com/)

## Install to Chrome / Edge

1. Clone the repo to the local machine
2. Install dependencies
   ```
   $ yarn install
   ```
3. Build the code
   ```
   $ yarn build
   ```
4. Open the browser extension page
   - <chrome://extensions/> or
   - <edge://extensions/>
5. Enable the **Developer Mode**
6. Click the **Load Unpacked**
7. Select the `public` directory under the project directory
8. Your will see an DLTS icon in the extension area of the toolbar.

## Configure

1. Right click the extension icon, select the **Options** / **Extension Options**
2. Fill the **Sign** with the same value in dashboard config.
3. Click **Save**

## Mock the Current User

1. In DLTS dashboard, click the extension icon.
2. Fill the **User Email** in the popup, with the email address you want to mock.
3. Click **Mock**, a permission request might be prompted.
4. The page should be refreshed automatically, with the mocked user signed in.
