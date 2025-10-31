const path = require('path');
const HtmlWebpackPlugin = require('html-webpack-plugin');
const CleanWebpackPlugin = require('clean-webpack-plugin');

module.exports = (env, argv) => {
  const isProduction = argv.mode === 'production';

  return {
    mode: argv.mode || 'development',
    entry: './src/main.tsx',
    output: {
      path: path.resolve(__dirname, 'dist'),
      filename: isProduction ? '[name].[hash].js' : '[name].js',
      publicPath: '/',
    },
    resolve: {
      extensions: ['.ts', '.tsx', '.js', '.jsx'],
      alias: {
        '@': path.resolve(__dirname, 'src'),
        '@/types': path.resolve(__dirname, 'src/types'),
        '@/components': path.resolve(__dirname, 'src/components'),
        '@/services': path.resolve(__dirname, 'src/services'),
        '@bbc/react-transcript-editor': path.resolve(__dirname, '../react-transcript-editor/packages/components/transcript-editor'),
      },
    },
    module: {
      rules: [
        {
          test: /\.tsx?$/,
          exclude: /node_modules/,
          use: [
            {
              loader: 'babel-loader',
              options: {
                presets: [
                  ['@babel/preset-env', { targets: 'defaults' }],
                  ['@babel/preset-react', { runtime: 'classic' }],
                  ['@babel/preset-typescript', { isTSX: true, allExtensions: true }],
                ],
                plugins: [
                  '@babel/plugin-proposal-optional-chaining',
                  '@babel/plugin-proposal-nullish-coalescing-operator',
                ],
              },
            },
          ],
        },
        {
          test: /\.jsx?$/,
          include: path.resolve(__dirname, '../react-transcript-editor'),
          use: [
            {
              loader: 'babel-loader',
              options: {
                presets: [
                  ['@babel/preset-env', { targets: 'defaults' }],
                  ['@babel/preset-react', { runtime: 'classic' }],
                ],
                plugins: [
                  '@babel/plugin-proposal-class-properties',
                  '@babel/plugin-proposal-object-rest-spread',
                ],
              },
            },
          ],
        },
        {
          test: /\.module\.(sa|sc)ss$/,
          include: path.resolve(__dirname, '../react-transcript-editor'),
          use: [
            'style-loader',
            {
              loader: 'css-loader',
              options: { modules: true, sourceMap: true }
            },
            {
              loader: 'sass-loader',
              options: { sourceMap: true }
            }
          ]
        },
        {
          test: /\.module\.css$/,
          include: path.resolve(__dirname, '../react-transcript-editor'),
          use: [
            'style-loader',
            {
              loader: 'css-loader',
              options: { modules: true, sourceMap: true }
            }
          ]
        },
        {
          test: /\.s(a|c)ss$/,
          include: path.resolve(__dirname, '../react-transcript-editor'),
          exclude: /\.module\.(s(a|c)ss)$/,
          use: [
            'style-loader',
            {
              loader: 'css-loader',
              options: { sourceMap: true }
            },
            {
              loader: 'sass-loader',
              options: { sourceMap: true }
            }
          ]
        },
        {
          test: /\.css$/,
          exclude: /\.module\.css$/,
          use: ['style-loader', 'css-loader'],
        },
        {
          test: /\.(svg|png|jpg|gif)$/,
          loader: 'file-loader',
          options: {
            name: '[name].[hash].[ext]',
            outputPath: 'assets/',
          },
        },
      ],
    },
    plugins: [
      new CleanWebpackPlugin.CleanWebpackPlugin(),
      new HtmlWebpackPlugin({
        template: './index.html',
        inject: 'body',
      }),
    ],
    devServer: {
      port: 3000,
      hot: true,
      open: false,
      historyApiFallback: true,
      proxy: {
        '/api': {
          target: 'http://localhost:8000',
          changeOrigin: true,
        },
      },
    },
    devtool: isProduction ? 'source-map' : 'eval-source-map',
  };
};

