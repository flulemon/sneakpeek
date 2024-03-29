const { configure } = require('quasar/wrappers');
const MonacoWebpackPlugin = require('monaco-editor-webpack-plugin');

module.exports = configure(function (ctx) {
  return {
    eslint: {
      warnings: true,
      errors: true
    },
    boot: [
    ],
    css: [
      'app.scss'
    ],
    extras: [
      'fontawesome-v6',
      'roboto-font',
      'material-icons',
    ],
    build: {
      target: {
        browser: [ 'es2019', 'edge88', 'firefox78', 'chrome87', 'safari13.1' ],
        node: 'node16'
      },
      distDir: '../sneakpeek/static/ui/',
      vueRouterMode: 'hash',
      env: {
        JSONRPC_ENDPOINT: ctx.dev ? 'http://localhost:8080/api/v1/jsonrpc' : '/api/v1/jsonrpc',
      },
      chainWebpack: config => {
        config.plugin('monaco-editor').use(MonacoWebpackPlugin, [
          {
            languages: ['python', 'javascript', 'html', 'xml']
          }
        ])
      }
    },
    devServer: {
      open: true
    },
    framework: {
      config: {
        dark: "auto",
        notify: {
          position: "bottom"
        }
      },
      plugins: [
        "Notify",
        "SessionStorage",
      ]
    },
    ssr: {
      pwa: false,
      prodPort: 3000,
      middlewares: [
        'render'
      ]
    },
    pwa: {
      workboxMode: 'generateSW',
      injectPwaMetaTags: true,
      swFilename: 'sw.js',
      manifestFilename: 'manifest.json',
      useCredentialsForManifestTag: false,
    },
    capacitor: {
      hideSplashscreen: true
    },
  }
});
