---
# LEGACY single-file command → /<filename> (subfolders → /<folder>:<file>). Accepts the same frontmatter as skills.
description: "{{what it does}}"
argument-hint: "[args]"
allowed-tools: Read Grep Bash(git status *)
disable-model-invocation: true
model: inherit
---
{{Prompt. Use $ARGUMENTS / $0 / $1, and !`shell` for dynamic context.}}
