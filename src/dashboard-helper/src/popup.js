/* eslint-env webextensions */

import jsrsasign from 'jsrsasign'

chrome.storage.local.get({ sign: '' }, function (items) {
  chrome.tabs.query({ active: true, currentWindow: true }, function (tabs) {
    const tab = tabs[0]
    if (tab == null || tab.url == null) return

    const $mockCurrentUserForm = document.querySelector('form#mock-current-user')
    $mockCurrentUserForm.addEventListener('submit', function (event) {
      event.preventDefault()

      chrome.permissions.request({
        permissions: ['cookies'],
        origins: [tab.url]
      }, function (granted) {
        if (!granted) return

        const email = $mockCurrentUserForm.elements.email.value
        const payload = {
          email,
          givenName: email.split('@', 1)[0],
          familyName: 'Mocked'
        }

        const token = jsrsasign.KJUR.jws.JWS.sign('HS256', {
          typ: 'JWT'
        }, payload, { utf8: items.sign })

        chrome.cookies.set({
          url: tab.url,
          name: 'token',
          value: token
        }, function (cookie) {
          if (cookie == null) return
          chrome.tabs.executeScript({
            code: 'window.localStorage.removeItem("teams"); window.location.reload(true); 0;'
          }, function (result) {
            if (result != null && result[0] === 0) {
              window.close()
            }
          })
        })
      })
    })
  })
})
