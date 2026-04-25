const path = require("path");
const HtmlWebpackPlugin = require("html-webpack-plugin");

module.exports = {
  entry: "./src/index.jsx",
  output: {
    path:       path.resolve(__dirname, "dist"),
    filename:   "bundle.[contenthash].js",
    publicPath: "/",
    clean:      true,
  },
  resolve: { extensions: [".js", ".jsx"] },
  module: {
    rules: [
      { test: /\.jsx?$/, use: "babel-loader", exclude: /node_modules/ },
      { test: /\.css$/,  use: ["style-loader", "css-loader"] },
    ],
  },
  plugins: [
    new HtmlWebpackPlugin({ template: "./public/index.html", title: "PC4 Drone Dashboard" }),
  ],
  devServer: {
    port:               3000,
    historyApiFallback: true,
    proxy: [
      { context: ["/api/feedback"],   target: "http://localhost:8005", pathRewrite: { "^/api/feedback": "" } },
      { context: ["/api/websocket"],  target: "http://localhost:8006",  ws: true,  pathRewrite: { "^/api/websocket": "" } },
    ],
  },
};