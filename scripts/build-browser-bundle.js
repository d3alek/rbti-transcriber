/**
 * Build a browser-compatible UMD bundle of react-transcript-editor.
 * This creates a standalone bundle that can be loaded in HTML via <script> tag.
 * 
 * Note: This builds from source. The dist/ files are CommonJS modules for npm,
 * but we need a UMD bundle for browser use.
 * 
 * Prerequisites:
 *   cd react-transcript-editor
 *   npm install --save-dev webpack webpack-cli babel-loader @babel/core @babel/preset-env @babel/preset-react style-loader css-loader sass-loader node-sass
 */

const path = require('path');
const fs = require('fs');

// Try to resolve webpack from react-transcript-editor/node_modules first
const reactEditorPath = path.resolve(__dirname, '../react-transcript-editor');
const nodeModulesPath = path.join(reactEditorPath, 'node_modules');

// Try to load webpack - first from react-transcript-editor, then globally
let webpack;
try {
  // Try from react-transcript-editor/node_modules
  webpack = require(path.join(nodeModulesPath, 'webpack'));
} catch (err1) {
  try {
    // Try global/webpack in current directory
    webpack = require('webpack');
  } catch (err2) {
    console.error('❌ Error: webpack is not installed');
    console.error('');
    console.error('Please install the required dependencies first:');
    console.error('  cd react-transcript-editor');
    console.error('  npm install --save-dev webpack webpack-cli babel-loader @babel/core @babel/preset-env @babel/preset-react style-loader css-loader sass-loader node-sass');
    console.error('');
    console.error('Then run this script from the react-transcript-editor directory:');
    console.error('  cd react-transcript-editor');
    console.error('  node ../scripts/build-browser-bundle.js');
    console.error('');
    process.exit(1);
  }
}

// Build browser bundle directly from source
// Note: We don't use the dist/ files (which are CommonJS for npm) as we need UMD for browser
console.log('🔨 Building browser UMD bundle from source...');

// Simple webpack config for browser bundle
const config = {
  mode: 'production',
  entry: path.resolve(__dirname, '../react-transcript-editor/packages/components/transcript-editor/index.js'),
  output: {
    path: path.resolve(__dirname, '../gh-pages-output/bundles'),
    filename: 'react-transcript-editor-bundle.js',
    library: 'ReactTranscriptEditor',
    libraryTarget: 'umd',
    globalObject: 'this',
  },
  externals: {
    'react': {
      commonjs: 'react',
      commonjs2: 'react',
      amd: 'React',
      root: 'React'
    },
    'react-dom': {
      commonjs: 'react-dom',
      commonjs2: 'react-dom',
      amd: 'ReactDOM',
      root: 'ReactDOM'
    }
  },
  module: {
    rules: [
      {
        test: /\.(js|jsx)$/,
        exclude: /node_modules/,
        use: {
          loader: 'babel-loader',
          options: {
            presets: ['@babel/preset-env', '@babel/preset-react']
          }
        }
      },
      {
        test: /\.module\.(sa|sc|c)ss$/,
        use: [
          'style-loader',
          {
            loader: 'css-loader',
            options: { 
              modules: true,
              localIdentName: '[local]--[hash:base64:5]'
            }
          },
          'sass-loader'
        ]
      },
      {
        test: /\.(css|scss|sass)$/,
        exclude: /\.module\.(sa|sc|c)ss$/,
        use: ['style-loader', 'css-loader', 'sass-loader']
      }
    ]
  },
  resolve: {
    extensions: ['.js', '.jsx'],
    modules: [nodeModulesPath, 'node_modules'],
    alias: {
      'react': path.join(nodeModulesPath, 'react'),
      'react-dom': path.join(nodeModulesPath, 'react-dom')
    }
  },
  resolveLoader: {
    modules: [nodeModulesPath, 'node_modules']
  },
  plugins: [
    new webpack.DefinePlugin({
      'process.env.NODE_ENV': JSON.stringify('production')
    })
  ]
};

webpack(config, (err, stats) => {
  if (err || stats.hasErrors()) {
    console.error('Error building bundle:', err || stats.compilation.errors);
    process.exit(1);
  }
  console.log('✅ Browser bundle built successfully');
  console.log(stats.toString({ colors: true }));
});

