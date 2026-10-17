---
name: humanizer
description: Rewrite AI-sounding text so it reads like a person wrote it, without changing what it says. Mandatory final pass after the direct-response-copywriting skill produces or edits any copy. Also use whenever the user asks to humanize, de-AI, or clean up prose with tells like not-X-but-Y contrasts, one-line closers, forced triads, em dashes, inflated claims, stock AI words, or bold labels.
---

# Humanizer

Vendored from [blader/humanizer](https://github.com/blader/humanizer) v3.1.0, commit `225a6f3` (MIT, see `LICENSE`).
Method and the 26 numbered patterns: `references/patterns.md`. Read it in full before every run; this file adds project rules only.

## Workflow

Follow `references/patterns.md` → "How to work":
1. Mark tells, strongest first (§1–§5 act on one sighting).
2. Draft the rewrite. Keep every supported claim; add nothing.
3. Check: read aloud, then re-hunt the usual survivors (§1 contrasts, §2 closers, §6 triads, §8 dashes, §19 bold labels).
4. Write the final version.

Output modes are as defined upstream: pasted text (draft + remaining patterns + final), file mode (write the final text only, prose only), embedded mode (final text only).

## Copywriting mode (after direct-response-copywriting)

Persuasive copy uses some devices on purpose. Strip the AI defaults, keep the selling mechanics:

- **Never change the substance:** offer terms, prices, numbers, guarantees, dates, proof, testimonials, mechanism, CTA, or the customer's own quoted words.
- **Keep a contrast** when both halves carry information or the negative half answers a real objection or enemy ("they don't write songs about Volvos"). Cut contrasts that only add weight (§1).
- **Keep short punchy lines** when they add a new fact, number, or consequence. Cut closers that repeat (§2).
- **Keep triads** only when there really are three items (e.g. "raise twice the cash, hire twice the staff, spend twice as much on ads"). Otherwise vary the structure (§6).
- **Sales language (§16):** remove empty puffery (stunning, renowned, groundbreaking). Concrete specifics already satisfy the copywriting skill's "point, don't talk" rule.
- **No em or en dashes** in the final copy (§8) unless the brand's voice sample uses them.
- **Voice sample wins.** Treat `VOICE.md` (settings + examples) as the voice sample; also match brand copy or customer quotes.
- Re-run the copywriting critique checklist items 10–12 and 18 after humanizing, so clarity and specificity survived the rewrite.

Then return the final copy in the format the copywriting task asked for.
