// Saved dynamic workflow, run as /audit-codebase with args {dir, concern}.
// Example: "Run /audit-codebase on src/ for missing input validation"
export const meta = {
  name: 'audit-codebase',
  description: 'Fan out one auditor per file under a directory for a single concern, then aggregate',
  phases: [{ title: 'Enumerate' }, { title: 'Audit' }],
}

const dir = (args && args.dir) || 'src'
const concern = (args && args.concern) || 'missing error handling'   // TODO(stub): default concern

phase('Enumerate')
const list = await agent(`List every source file under ${dir}/ (skip tests, generated files, and vendored code).`, {
  label: 'enumerate',
  schema: { type: 'object', required: ['files'], properties: { files: { type: 'array', items: { type: 'string' } } } },
})

const audits = await pipeline(list?.files || [], file =>
  agent(`Audit ${file} ONLY for: ${concern}. Reply "none" if clean; otherwise give path:line and a fix for each issue.`, {
    label: file,
    phase: 'Audit',
  }),
)

return audits.filter(a => a && !/^\s*none\s*$/i.test(String(a)))
