const fs = require('fs')

const chokidar = require('chokidar')
const pino = require('pino')

/**
 * @param {import('http2').Http2SecureServer}
 */
module.exports = (server) => {
  const { SSL_KEY_FILE, SSL_CERT_FILE } = process.env

  const logger = pino({ name: 'https' })

  chokidar.watch([SSL_KEY_FILE, SSL_CERT_FILE], {
    disableGlobbing: true,
    depth: 0,
    awaitWriteFinish: true
  }).on('all', async (event, path) => {
    logger.info('%s %s', event, path)
    try {
      const [key, cert] = await Promise.all([
        fs.promises.readFile(SSL_KEY_FILE),
        fs.promises.readFile(SSL_CERT_FILE)
      ])
      server.setSecureContext({ key, cert })
    } catch (error) {
      logger.error(error.stack)
    }
  })
}
