const Ajv = require('ajv')

const validator = new Ajv()
validator.addSchema(require('./status.schema'), 'status')
validator.addSchema(require('./command.schema'), 'command')
validator.addSchema(require('./endpoints.schema'), 'endpoints')
validator.addSchema(require('./job.schema'), 'job')
validator.addSchema(require('./template.schema'), 'template')
validator.addSchema(require('./priority.schema'), 'priority')
validator.addSchema(require('./timeout.schema'), 'timeout')
validator.addSchema(require('./batch-status.schema'), 'batch-status')
validator.addSchema(require('./meta.schema'), 'meta')
validator.addSchema(require('./key.schema'), 'key')

module.exports = validator
