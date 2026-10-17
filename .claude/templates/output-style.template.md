---
name: "{{Style Name}}"               # Shown in the /config picker. Default: file name.
description: "{{One line for the picker}}"
keep-coding-instructions: true       # true = keep Claude Code's built-in software-engineering instructions. Default false (replaces them).
# force-for-plugin: false            # Plugin output styles only: auto-apply when the plugin is enabled.
---

# {{Style Name}}

<!-- The body is added to the system prompt. Activate with /config or "outputStyle": "{{Style Name}}" in settings. -->

- {{tone}}
- {{structure / length}}
- {{what to always include}}
