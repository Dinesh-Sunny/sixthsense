#!/usr/bin/env bash
# statusLine command. Gets session JSON on stdin and prints ONE line (ANSI colors allowed).
# Input fields: model.display_name, workspace.current_dir/project_dir/git_worktree, cost.total_cost_usd,
#               context_window.used_percentage, output_style.name, version, session_name ...
# Docs: https://code.claude.com/docs/en/statusline
input="$(cat)"
j() { printf '%s' "$input" | jq -r "$1 // empty" 2>/dev/null; }
model="$(j '.model.display_name')"
dir="$(basename "$(j '.workspace.current_dir')")"
ctx="$(j '.context_window.used_percentage')"
cost="$(j '.cost.total_cost_usd')"
branch="$(git -C "$(j '.workspace.current_dir')" branch --show-current 2>/dev/null || true)"

line="\033[36m${model:-?}\033[0m  ${dir}"
[[ -n "$branch" ]] && line+="  \033[33m⎇ $branch\033[0m"
[[ -n "$ctx" ]]    && line+="  ctx ${ctx%.*}%"
[[ -n "$cost" ]]   && line+="  \$$(printf '%.2f' "$cost")"
printf '%b\n' "$line"
