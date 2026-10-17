// Saved dynamic workflow, run as /review-branch [base].
// Docs: https://code.claude.com/docs/en/workflows  ·  Load /workflow-authoring before editing.
// Rules: `meta` must be the first statement and a pure literal. Date.now()/Math.random() throw; pass values via args.
export const meta = {
  name: 'review-branch',
  description: 'Review every changed file on this branch in parallel, verify findings, write one summary',
  phases: [
    { title: 'Discover', detail: 'List changed files' },
    { title: 'Review', detail: 'One reviewer per file' },
    { title: 'Verify', detail: 'Adversarially check each finding' },
  ],
}

const base = (args && args.base) || 'origin/HEAD'

const FILES = { type: 'object', required: ['files'], properties: { files: { type: 'array', items: { type: 'string' } } } }
const FINDINGS = {
  type: 'object',
  required: ['findings'],
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        required: ['file', 'line', 'severity', 'problem', 'fix'],
        properties: {
          file: { type: 'string' }, line: { type: 'integer' },
          severity: { type: 'string', enum: ['blocker', 'major', 'minor', 'nit'] },
          problem: { type: 'string' }, fix: { type: 'string' },
        },
      },
    },
  },
}
const VERDICT = { type: 'object', required: ['isReal', 'reason'], properties: { isReal: { type: 'boolean' }, reason: { type: 'string' } } }

phase('Discover')
const found = await agent(
  `Run \`git diff --name-only $(git merge-base HEAD ${base})\` and return the changed source files (exclude lockfiles and generated files).`,
  { label: 'discover', schema: FILES },
)
if (!found || found.files.length === 0) return { summary: 'No changed files.' }
log(`Reviewing ${found.files.length} files against ${base}`)

const results = await pipeline(
  found.files,
  file => agent(
    `Review ${file} (full file + its diff vs ${base}) for bugs, security issues, and violations of .claude/rules. Only report issues with a concrete failure scenario.`,
    { label: `review:${file}`, phase: 'Review', schema: FINDINGS },
  ),
  review => parallel((review?.findings || []).map(f => () =>
    agent(
      `Try to DISPROVE this finding by reading the code: ${JSON.stringify(f)}. Return isReal=false if it is wrong or not reachable.`,
      { label: `verify:${f.file}:${f.line}`, phase: 'Verify', schema: VERDICT },
    ).then(v => (v && v.isReal ? f : null)),
  )),
)

const confirmed = results.flat().filter(Boolean)
return { base, files: found.files.length, confirmed }
