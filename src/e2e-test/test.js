const puppeteer = require('puppeteer')
const _ = require('lodash')

const {
  PUPPETEER_HEADLESS,
  PUPPETEER_USER_DATA_DIR = '.puppeteer',
  DLTS_DASHBOARD_URL,
  DLTS_CLUSTER_ID
} = process.env

/** @type {import('puppeteer').Browser} */
let browser

describe('Deep Learning Training Service', function () {
  before(async function () {
    browser = await puppeteer.launch(({
      headless: PUPPETEER_HEADLESS !== 'false',
      userDataDir: PUPPETEER_USER_DATA_DIR
    }))
  })

  after(async function () {
    await browser.close()
  })

  describe('Submit CPU Job', function () {
    const MESSAGE = 'A quick movement of the enemy will jeopardize six gunboats.'

    /** @type {import('puppeteer').Page} */
    let page

    before(async function () {
      page = await browser.newPage()
    })

    it('sign in', async function () {
      this.timeout('1m')
      await page.goto(DLTS_DASHBOARD_URL)

      await (
        await page.waitForSelector('a[href^="/api/authenticate"]')
      ).click()

      await page.waitForFunction(
        url => window.location.origin === url,
        { polling: 'mutation' }, DLTS_DASHBOARD_URL)

      await (
        await page.waitForSelector('header h1')
      ).evaluate(node => node.textContent)
        .should.eventually.equal('DLTS')
    })

    it('submit job', async function () {
      await (
        await page.waitForSelector('a[href="/submission/training"]')
      ).click()

      await page.waitForFunction(
        () => window.location.pathname === '/submission/training',
        { polling: 'mutation' })

      await (
        await page.waitForSelector('form div.MuiGrid-item:nth-child(1) div.MuiSelect-root')
      ).click()

      await (
        await page.waitForSelector(`.MuiPopover-paper [data-value="${DLTS_CLUSTER_ID}"]`)
      ).click()

      await page.$eval('form div.MuiGrid-item:nth-child(1) div.MuiSelect-root', $div => $div.textContent)
        .should.eventually.equal(DLTS_CLUSTER_ID)

      await (
        await page.waitForSelector('form div.MuiGrid-item:nth-child(2) input')
      ).type('e2e-test', { delay: 10 })

      await (
        await page.waitForSelector('form div.MuiGrid-item:nth-child(7) input')
      ).type('debian', { delay: 10 })

      await (
        await page.waitForSelector('form div.MuiGrid-item:nth-child(8) textarea')
      ).type(`echo "${MESSAGE}"`, { delay: 10 })

      await (
        await page.waitForSelector('form button[type="submit"]')
      ).click()
    })

    it('retrieve job log', async function () {
      this.timeout('10m')
      await page.waitForFunction(() => {
        const $chip = window.document.querySelector('.MuiChip-root')
        if ($chip == null) return false
        return $chip.textContent === 'Finished'
      }, { polling: 'mutation', timeout: 0 })

      await (
        await page.waitForSelector('.MuiTabs-root .MuiTab-root:nth-child(4)')
      ).click()
      await (
        await page.waitForSelector('textarea:nth-child(1)')
      ).evaluate(node => node.textContent)
        .should.eventually.containEql(MESSAGE)
    })

    afterEach(async function () {
      if (this.currentTest && this.currentTest.err) {
        const filename = _.snakeCase(`${new Date().toISOString()}_${this.currentTest.fullTitle()}`)
        await page.screenshot({
          path: `${PUPPETEER_USER_DATA_DIR}/${filename}.png`,
          fullPage: true
        })
      }
    })

    after(async function () {
      await page.close()
    })
  })
})
