# Founder example ideas (input_examples for v4)

Owner: Narin · Drafted Oct 25, 2026 from two one-line ideas. Every number below is **assumed** unless Narin replaces it. Example inputs are text only: no real child audio or personal data ever enters the tool.

---

## Idea A — Speech-building voice app for autistic children with speech delays

**Idea:** A voice app that helps autistic children with speech delays form simple sentences and build on them step by step, reinforcing comprehension as sentences grow.
**Target user:** Parents, with speech-language therapists as secondary users.
**Quality bar (rubric):** target sentences at or below the child's current length (level 1: ≤ 3 words; level 2: ≤ 5); concrete, familiar nouns; feedback always positive and specific; no diagnostic or clinical claims; output in plain language a parent can read.

| # | AI feature | Modality | Example input | Mode | Uses / user / month (assumed) |
|---|---|---|---|---|---|
| A1 | Transcribe the child's attempt | audio in → text | ~5 s utterance | interactive | 240 (12 sessions × 20 attempts) |
| A2 | Choose the next target sentence and give feedback | text → text | "Level 2. Target: 'I want red ball.' Child said: 'want ball.'" | interactive | 240 |
| A3 | Speak the target sentence aloud | text → audio out | ~3 s of speech | interactive | 240 |
| A4 | Weekly progress summary for parent/therapist | text → text | One week of session logs (de-identified) | **background** (batch-eligible) | 4 |

**Assumed growth:** 50 → 500 → 5,000 → 50,000 families. **AI budget ceiling:** unknown. **Price:** unknown (cost-only report).

**What this idea tests in the tool**
- **Audio economics.** A1 and A3 are priced per second of audio. That's the session's modality method, automated. Audio components are *estimated* from published per-second conversions. Only A2 and A4 are *measured* through Nightshift. The pack says which is which.
- **Cost driver.** At 240 uses per child per month, the per-attempt loop dominates. The tool should show whether A2 can move to Nemotron without failing the rubric, and when.
- **Non-cost stack alternative.** On-device or self-hosted open-source speech recognition keeps a child's voice off third-party servers. The tool should list it as a privacy-driven stack option, not only a cost option.
- **Risks the tool should flag (not legal advice):** children's voice data and parental consent (e.g. COPPA in the US); health-adjacent use if therapists are involved; the app supports therapy and does not replace it.

---

## Idea B — Agent-to-agent micropayment gateway using cryptocurrency

**Idea:** A payment system that lets AI agents pay other AI agents for services in microtransactions, settled in cryptocurrency.
**Target user:** Developers of AI agents that buy or sell services (data lookups, model calls, tool use).
**Quality bar (rubric):** parsed quotes match the request exactly (service, quantity, max price); no invented terms; anomaly explanations cite the triggering signals; summaries never state facts not in the transaction record.

| # | AI feature | Modality | Example input | Mode | Uses (assumed) |
|---|---|---|---|---|---|
| B1 | Parse an agent's service request into a structured quote | text → JSON | "Need 200 geocoding lookups, pay ≤ $0.40 total" | interactive, **per transaction** | 10,000 transactions per active agent per month |
| B2 | Explain a flagged transaction | text → text | Transaction record + anomaly signals | background | 1% of transactions |
| B3 | Dispute or receipt summary | text → text | Transaction thread | on demand | 0.1% of transactions |

**Assumed growth:** 50 → 500 → 5,000 → 50,000 active agents. **Average transaction value (assumed):** $0.02. **Gateway take rate (assumed):** 1%, i.e. $0.0002 revenue per transaction.

**What this idea tests in the tool**
- **Unit economics per action.** If B1 runs an LLM on every transaction, AI cost per transaction can exceed the gateway's revenue per transaction many times over. The tool should compute AI cost as a share of revenue per use, and recommend keeping the model off the hot path: deterministic parsing first, LLM only on failures, or a small open model.
- **AI is not the main cost here.** Chain fees, custody, compliance (KYC/AML) and money-transmission licensing likely dominate. The tool doesn't model them. It must list them as **evidence gaps**, not leave a reader thinking the AI line is the whole bill.
- **Risk the tool should flag (not legal or financial advice):** regulatory exposure for moving money is a gating question before cost optimization matters.

---

## Why these two make a good pair for the demo

They teach opposite lessons. Idea A shows a high-frequency, multimodal app where model choice and audio pricing drive cost as it grows. Idea B shows an app where the right answer is "keep AI off the per-transaction path; your real costs are elsewhere." A tool that gives both answers honestly is exercising judgment, not filling in a spreadsheet.

## Founder-impact record (fill after running each)

| Idea | My plan before | What the tool recommended | Did it change my plan? Why? |
|---|---|---|---|
| A | | | |
| B | | | |
