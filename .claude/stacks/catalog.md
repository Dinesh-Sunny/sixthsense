# Stack catalog
Researched registry rows from earlier projects (first: agentic-teams, 2026-10-05). Shared via
playbook-sync. `stacks.sh bootstrap` copies a row's docs and AI tooling into a project's registry
for the packages that project declares; version, choke point and health are set per project.
Add a row here when a project researches a new stack (the /feature Learn step).

## Stacks
| stack | packages | version | docs | outline | ai_tooling | choke point | health |
|---|---|---|---|---|---|---|---|
| langchain | langchain, langchain-core, langchain-openai, langchain-anthropic | uv.lock:langchain | mcp docs-langchain + reference-langchain | langchain | mcp:docs-langchain; mcp:reference-langchain; skill:langchain-ai/langchain-skills; llms:https://docs.langchain.com/llms.txt | — | catalog |
| langgraph | langgraph, langgraph-cli, langgraph-api | uv.lock:langgraph | mcp docs-langchain + reference-langchain | langgraph | mcp:docs-langchain; mcp:reference-langchain; skill:langchain-ai/langchain-skills; cli:langgraph; llms:https://docs.langchain.com/llms.txt | — | catalog |
| langsmith | langsmith | uv.lock:langsmith | mcp docs-langchain | langsmith | mcp:langsmith; mcp:docs-langchain; cli:langsmith; skill?:https://github.com/langchain-ai/langsmith-skills; llms:https://docs.langchain.com/llms.txt | — | catalog |
| langfuse | langfuse | uv.lock:langfuse | llms.txt; docs .md pages; REST search | langfuse | llms:https://langfuse.com/llms.txt; mcp?:langfuse-docs https://langfuse.com/api/mcp; skill?:https://github.com/langfuse/skills/tree/main/skills/langfuse; cli:npx @langfuse/cli | — | catalog |
| langchain-js | @langchain/langgraph-sdk, @langchain/react, @langchain/core | pnpm-lock:@langchain/langgraph-sdk | mcp docs-langchain (javascript) | langchain-js | mcp:docs-langchain; mcp:reference-langchain; skill:langchain-ai/langchain-skills; llms:https://docs.langchain.com/llms.txt | — | catalog |
| next | next, eslint-config-next | pnpm-lock:next | mcp next-devtools; bundled docs | next | mcp:next-devtools; skill?:https://github.com/vercel/next.js/tree/canary/skills; llms:https://nextjs.org/docs/llms.txt; cli:agent-browser; agents-md:web/AGENTS.md | — | catalog |
| react | react, react-dom, @types/react, @types/react-dom | pnpm-lock:react | llms.txt | react | llms:https://react.dev/llms.txt | — | catalog |
| assistant-ui | @assistant-ui/react, @assistant-ui/react-langchain, @assistant-ui/react-markdown, assistant-stream, tw-shimmer, remark-gfm | pnpm-lock:@assistant-ui/react | llms.txt | assistant-ui | mcp:assistant-ui; llms:https://www.assistant-ui.com/llms.txt; agents-md:https://www.assistant-ui.com/AGENTS.md | — | catalog |
| shadcn-ui | shadcn, radix-ui, class-variance-authority, cn, tailwindcss, @tailwindcss/postcss, tw-animate-css, prettier-plugin-tailwindcss | pnpm-lock:shadcn | mcp shadcn; context7 (radix, tailwind) | shadcn-ui | mcp:shadcn; llms:https://ui.shadcn.com/llms.txt; skill?:https://ui.shadcn.com/docs/skills (user-scope personal copy); cli:shadcn info --json | — | catalog |
| react-bits | motion, ogl | pnpm-lock:motion | llms.txt | react-bits | mcp:motion; mcp:shadcn; skill?:https://github.com/motiondivision/ai-kit; llms:https://reactbits.dev/llms.txt; llms:https://motion.dev/llms.txt | — | catalog |
| zustand | zustand | pnpm-lock:zustand | llms.txt | zustand | llms:https://zustand.docs.pmnd.rs/llms.txt | — | catalog |
| web-testing | vitest, @vitejs/plugin-react, jsdom, @testing-library/react, @testing-library/dom | pnpm-lock:vitest | llms.txt; context7 (testing-library) | web-testing | llms:https://vitest.dev/llms.txt | — | catalog |
| web-tooling | eslint, prettier, typescript, @types/node | pnpm-lock:eslint | eslint.org v9 docs; llms.txt (prettier); typescriptlang.org + TypeScript-Website repo | web-tooling | mcp?:eslint npx -y @eslint/mcp@0.3.13; llms:https://prettier.io/llms.txt | — | catalog |
| freellmapi | (image) | compose:freellmapi | GitHub repo at tag | freellmapi | mcp?:freellmapi http://127.0.0.1:3001/mcp | — | catalog |
| omniroute | (image) | compose:omniroute | GitHub repo at tag | omniroute | mcp?:omniroute http://localhost:20128/api/mcp/stream; skill?:https://github.com/diegosouzapw/OmniRoute/tree/3.8.51/skills; agents-md:https://github.com/diegosouzapw/OmniRoute/blob/3.8.51/AGENTS.md | — | catalog |
| uv | uv_build | tool:uv | llms.txt | uv | llms:https://docs.astral.sh/uv/llms.txt; skill?:https://github.com/astral-sh/claude-code-plugins | — | catalog |
| ruff | ruff | uv.lock:ruff | llms.txt | ruff | llms:https://docs.astral.sh/ruff/llms.txt | — | catalog |
| mypy | mypy | uv.lock:mypy | context7 | mypy | none (checked 2026-10-05) | — | catalog |
| pytest | pytest, anyio | uv.lock:pytest | context7 | pytest | none (checked 2026-10-05) | — | catalog |
| httpx | httpx | uv.lock:httpx | context7 | none (utility) | none (checked 2026-10-05) | — | catalog |
| python-dotenv | python-dotenv | uv.lock:python-dotenv | context7 | none (utility) | none (checked 2026-10-05) | — | catalog |
| pyyaml | pyyaml | uv.lock:pyyaml | context7 | none (utility) | none (checked 2026-10-05) | — | catalog |
| packaging | packaging | uv.lock:packaging | context7 | none (utility) | none (checked 2026-10-05) | — | catalog |
| openai | openai | uv.lock:openai | context7 | none (utility) | none (checked 2026-10-05) | — | catalog |
| icons | @hugeicons/core-free-icons, @hugeicons/react, lucide-react | pnpm-lock:@hugeicons/react | context7 | none (utility) | none (checked 2026-10-05) | — | catalog |
| next-themes | next-themes | pnpm-lock:next-themes | context7 | none (utility) | none (checked 2026-10-05) | — | catalog |
