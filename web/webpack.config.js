const path = require('path');
const HtmlWebpackPlugin = require('html-webpack-plugin');
const VueLoaderPlugin = require('vue-loader/lib/plugin')

module.exports = {
    entry: ['./src/index.js'],
    //devtool: 'inline-source-map',
    devServer: {
        contentBase: './dist'
    },
    resolve: {
        alias: {
            'vue$': 'vue/dist/vue.esm.js' // this is important to enable Vue?
        },
        extensions: ['*', '.js', '.vue', '.json']
    },
    module: {
        rules: [
            {
                test: /\.vue$/,
                loader: 'vue-loader'
            },
            {
                test: /\.css$/,
                use: [
                    'style-loader',
                    'css-loader'
                ]
            },
            {
                test: /\.(png|svg|jpg|gif)$/,
                use: [
                    'file-loader'
                ]
            }, {
                test: /\.(woff|woff2|eot|ttf|otf)$/,
                use: [
                    'file-loader'
                ]
            }
        ]
    },
    plugins: [
        new HtmlWebpackPlugin({
            title: 'Node Monitor',
            template: 'src/index.html'
        }),
        new VueLoaderPlugin()
    ],
    output:
        {
            filename: 'bundle.js',
            path:
                path.resolve(__dirname, 'dist')
        }
}
;