/**
 * Build a browser-compatible UMD bundle of DeepgramTransformer.
 * This creates a standalone bundle that can be loaded in HTML via <script> tag.
 * 
 * This bundles DeepgramTransformer and its type dependencies into a single file
 * that can handle raw Deepgram format conversion in static bundles.
 */

const path = require('path');
const fs = require('fs');

// Try to resolve webpack from web-ui/node_modules first
const webUiPath = path.resolve(__dirname, '../web-ui');
const nodeModulesPath = path.join(webUiPath, 'node_modules');

// Try to load webpack - first from web-ui, then globally
let webpack;
try {
  webpack = require(path.join(nodeModulesPath, 'webpack'));
} catch (err1) {
  try {
    webpack = require('webpack');
  } catch (err2) {
    console.error('❌ Error: webpack is not installed');
    console.error('');
    console.error('Please install the required dependencies first:');
    console.error('  cd web-ui');
    console.error('  npm install');
    console.error('');
    process.exit(1);
  }
}

// Create a temporary entry file that exports DeepgramTransformer
const entryFile = path.join(__dirname, 'temp-deepgram-transformer-entry.ts');
const entryContent = [
  '// Entry point for DeepgramTransformer bundle',
  '// Export as a global variable for browser use',
  '',
  "import { DeepgramTransformer } from '../web-ui/src/services/DeepgramTransformer';",
  '',
  '// Export the class directly for UMD compatibility',
  '// This allows accessing as DeepgramTransformer directly, or DeepgramTransformer.DeepgramTransformer',
  'const exports = DeepgramTransformer;',
  '',
  '// Also set on window for direct access',
  "if (typeof window !== 'undefined') {",
  '  window.DeepgramTransformer = DeepgramTransformer;',
  '}',
  '',
  'export default DeepgramTransformer;',
  "export { DeepgramTransformer };"
].join('\n');

// Write entry file
fs.writeFileSync(entryFile, entryContent, 'utf8');

// Build browser bundle
console.log('🔨 Building DeepgramTransformer browser UMD bundle...');

const config = {
  mode: 'development',
  entry: entryFile,
  output: {
    path: path.resolve(__dirname, '../gh-pages-output/bundles'),
    filename: 'deepgram-transformer-bundle.js',
    library: 'DeepgramTransformer',
    libraryTarget: 'umd',
    globalObject: 'this',
  },
  externals: {
    // No externals - we want everything bundled
  },
  optimization: {
    minimize: false
  },
  devtool: 'source-map',
  module: {
    rules: [
      {
        test: /\.(ts|tsx|js|jsx)$/,
        exclude: /node_modules/,
        use: {
          loader: 'babel-loader',
          options: {
            presets: [
              [require.resolve('@babel/preset-env', { paths: [nodeModulesPath] }), { targets: { browsers: ['> 1%', 'last 2 versions'] } }],
              require.resolve('@babel/preset-typescript', { paths: [nodeModulesPath] }),
              require.resolve('@babel/preset-react', { paths: [nodeModulesPath] })
            ],
            plugins: [
              require.resolve('@babel/plugin-proposal-class-properties', { paths: [nodeModulesPath] }),
              require.resolve('@babel/plugin-proposal-object-rest-spread', { paths: [nodeModulesPath] }),
              require.resolve('@babel/plugin-proposal-optional-chaining', { paths: [nodeModulesPath] }),
              require.resolve('@babel/plugin-proposal-nullish-coalescing-operator', { paths: [nodeModulesPath] })
            ],
            cacheDirectory: false
          }
        }
      }
    ]
  },
  resolve: {
    extensions: ['.ts', '.tsx', '.js', '.jsx'],
    modules: [
      path.resolve(__dirname, '../web-ui/src'),
      path.resolve(__dirname, '..'),
      nodeModulesPath,
      'node_modules'
    ],
    alias: {
      // Resolve imports from web-ui/src
      '@': path.resolve(__dirname, '../web-ui/src')
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
  // Clean up entry file
  if (fs.existsSync(entryFile)) {
    fs.unlinkSync(entryFile);
  }
  
  if (err || stats.hasErrors()) {
    console.error('Error building bundle:', err || stats.compilation.errors);
    if (stats && stats.compilation && stats.compilation.errors) {
      stats.compilation.errors.forEach(error => {
        console.error('Build error:', error.message || error);
      });
    }
    process.exit(1);
  }
  console.log('✅ DeepgramTransformer bundle built successfully');
  console.log(stats.toString({ colors: true, chunks: false }));
  
  // Check if bundle file exists
  const bundlePath = path.resolve(__dirname, '../gh-pages-output/bundles/deepgram-transformer-bundle.js');
  if (fs.existsSync(bundlePath)) {
    const stats = fs.statSync(bundlePath);
    console.log(`📦 Bundle file size: ${(stats.size / 1024).toFixed(2)} KB`);
    
    // Check first few lines to verify it has UMD wrapper
    const bundleContent = fs.readFileSync(bundlePath, 'utf8').substring(0, 500);
    if (bundleContent.includes('DeepgramTransformer')) {
      console.log('✅ Bundle appears to contain DeepgramTransformer export');
    } else {
      console.warn('⚠️  Bundle may not contain DeepgramTransformer export');
    }
  } else {
    console.error('❌ Bundle file not found at:', bundlePath);
  }
});

