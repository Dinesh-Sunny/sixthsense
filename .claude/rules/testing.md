---
paths:
  - "**/*.test.*"
  - "**/*.spec.*"
  - "**/__tests__/**"
  - "tests/**"
  - "e2e/**"
---
<!-- last-verified: 2026-10-01 -->
<!-- Loads only when Claude reads a file matching the globs above. -->
# Testing

- Runner: UNIT_TEST_RUNNER; e2e: E2E_RUNNER. Single file: `TEST_FILE_CMD <path>`.
- Location: n/a for this hackathon project.
- Names: "should <expected> when <condition>".
- Arrange / Act / Assert. One behavior per test.
- Mock at the boundaries (network, time, randomness, FS). Don't mock the unit under test.
- Bug fix → write a failing test first, then fix.
- No `.only` / `.skip` committed. No sleeps; use fake timers or await conditions.
- Fixtures/factories live in FIXTURES_PATH.
