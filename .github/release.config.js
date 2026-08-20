module.exports = {
  branches: ["main"],
  plugins: [
    "@semantic-release/commit-analyzer",
    "@semantic-release/release-notes-generator",
    ["@semantic-release/changelog", { changelogFile: "CHANGELOG.md" }],
    ["@semantic-release/exec", { prepareCmd: "echo ${nextRelease.version} > VERSION && for d in services/*/; do echo ${nextRelease.version} > $d/VERSION; done" }],
    ["@semantic-release/git", { assets: ["CHANGELOG.md","VERSION","services/*/VERSION"], message: "chore(release): ${nextRelease.version} [skip ci]" }],
    "@semantic-release/github"
  ]
};
