# SixthSense

The interface for **SixthSense**, a video agent that watches camera footage, predicts what happens next, and checks itself against the next clip. The look borrows the calm of consumer AI products (inspired by Hark's visual language: soft cool neutrals, dark pill buttons, a serif wordmark, big rounded media), and keeps every bit of colour for one job: telling an operator what needs attention.

## Content fundamentals
Voice inspired by Airbnb's UX writing principles: **simple, precise, helpful, human**. SixthSense talks like a calm, capable host, never an alarm system.
- **Simple.** Everyday words, one idea per sentence. No pipeline words on screen (YOLO, Cosmos, segment, inference); keep them for "See how it decided".
- **Precise.** The real vehicle, the real number, the real time: "Gap closed from 3.4 to 0.6 car lengths in 2.1s".
- **Helpful.** Lead with what the person can do. Buttons are verbs that say what happens: View, Send alert, Watch a camera, Try again.
- **Human.** Calm, warm, never alarmist. Errors say what happened and what's safe: "We lost the connection. Your moments are safe."
- **Short labels.** Next · Why · Fix · Came true · Partly · Didn't happen · Checking soon.
- **Plain, specific, checkable.** A prediction names the vehicle and the action: "The white truck cuts in within 3 seconds", never "traffic continues".
- **Numbers are measured, never estimated.** Show `7 / 10 came true`, not "high accuracy". Sample data is labelled *Sample*.
- **Camera language.** Camera ids and timestamps in `data` mono: `i24_cam-1 · 00:41-00:46`.
- Sentence case everywhere except the `label` style on pills.

## Visual foundations
- **Ground and atmosphere.** Pages sit on `ground`; the top of the page carries a soft vertical wash from `sky-100` to `ground` (the Hark sky, made quieter). No other gradients.
- **Borders over shadows.** Cards are `surface` with a 1px `hairline` and `radius-md`. Only the hero video card may float with `shadow-soft` and `radius-lg`.
- **Everything you press is a pill.** Primary action: `pill` fill, `on-ink` text, `radius-pill`, 40px tall. Secondary: transparent with a `hairline` border.
- **Type.** `wordmark` and `display` in Instrument Serif (one display line per screen). Everything else Geist; data in Geist Mono with tabular numbers.
- **Colour means state.** `risk-high` / `risk-mid` / `risk-low` encode risk 5→1; `truth` is reserved for *came true*; `slate` for unknown or not yet checked. Never use them for decoration. States always pair colour with a word or icon.
- **Spacing.** 4px base; cards pad `space-4`, sit `space-6` apart; sections `space-8`.
- **Motion.** 150ms ease-out on hover and press; a 1.2s shimmer on loading skeletons; nothing else moves. Respect reduced motion.

## Iconography
Thin 1.5px line icons at 16px, drawn in `ink-muted`. No emoji in the product UI.

## Components
Button · Tabs · StatusPill · IncidentCard · AskBox · AlertRow · AccuracyMeter. Each has a live preview and guidelines.
