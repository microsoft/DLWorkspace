/* eslint-env webextensions */

const $form = document.querySelector('form')

chrome.storage.local.get({ sign: '' }, function (items) {
  $form.elements.sign.value = items.sign
})

$form.addEventListener('submit', function (event) {
  event.preventDefault()
  chrome.storage.local.set({ sign: $form.elements.sign.value })
})
