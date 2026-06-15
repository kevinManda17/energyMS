module.exports = function (api) {
  api.cache(true);
  return {
    // Use an absolute path so Metro's transform worker always resolves it,
    // regardless of its working directory.
    presets: [require.resolve("babel-preset-expo")],
  };
};
