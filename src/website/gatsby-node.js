const path = require('path')

exports.onCreateWebpackConfig = args => {
  args.actions.setWebpackConfig({
    resolve: {
      modules: [path.resolve(__dirname, '../node_modules'), 'node_modules'],
    },
  })
}
