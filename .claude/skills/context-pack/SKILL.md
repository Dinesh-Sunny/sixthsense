---
name: context-pack
description: Build a compact context pack for AI chats without repo access (ChatGPT, claude.ai Projects, Gemini). Optionally include one knowledge topic.
argument-hint: "[topic from docs/knowledge]"
model: haiku
effort: low
allowed-tools: Bash(python3 .claude/scripts/ctx.py pack *) Bash(python3 .claude/scripts/ctx.py pack)
---
<!-- last-verified: 2026-10-01 -->
# Context pack

Available topics: !`ls docs/knowledge 2>/dev/null | grep -v -e README -e archive | sed 's/\.md$//' | tr '\n' ' '`

1. With no topic given: `python3 .claude/scripts/ctx.py pack`. Otherwise: `python3 .claude/scripts/ctx.py pack --topic $ARGUMENTS`.
2. Report the output path and token estimate. Tell the user to upload it as project knowledge or paste it at the start of the chat.
3. Remind them it is a snapshot: regenerate after context changes. Never edit it by hand.
