module.exports = {
    mode: 'development',
    entry: './test.js',
    output: {
        path:　__dirname + '../static/js',
        filename: 'bundle.js'
    },
    module: {
        loaders: [
            {
                test: /\.js$/,
                exclude: /node_modules/,
                loader: "babel-loader",
                query:{
                    presets:['es2015']
                }
            }
        ]
    }
};