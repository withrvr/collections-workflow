# /brag plan: Collections Workflow

**What it is:** You upload an ERP export and get back the overdue collections position plus a data-quality report that explains every row it left out.
**Who it's for:** finance and collections teams who can't trust a total that was quietly computed from dirty data.
**What sets it apart:** a control gate refuses to call a run clean when more than 5% of rows are bad, and the AI only narrates. It never computes a rupee figure.
**Most impressive claim:** the sample file *blocks* at 47.2%, and that is the correct result.
**Visual hook:** a grid of 36 invoices where 17 flash red.
**Share caption:** "36 invoices, 17 problems, one report that refuses to pretend otherwise."

## Angle
An overdue report that won't lie to you. Each beat shows the app doing what it does with the sample workbook's own data: 36 invoices, 17 exceptions, a 47.2% exception rate, Rs 12,02,000.00 overdue, and West as the heaviest region.

## Tone
`polished` with a dry edge. Dark UI, the app's own teal (`#0d9488`), Inter, and calm motion with a few sharp moments when the gate blocks.

## Storyboard (23.0s, 1920×1080, 30fps)

| # | Time | Scene | On screen (real copy from the app) |
|---|---|---|---|
| 1 | 0.0–3.0 | **Hook** | Invoice grid INV-1001…INV-1036 slides in. The 17 rows that trip a rule flash red. Headline: "36 invoices. / 17 problems hiding inside." |
| 2 | 3.0–7.0 | **Reveal + upload** | Logo and "Collections Workflow". Upload card: "Upload a workbook", dropzone, `candidate_assessment_dataset.xlsx` drags in, report date 31-07-2026, cursor clicks **Run**. |
| 3 | 7.0–12.4 | **Control gate** | Run detail: six timeline stages tick in (Load workbook → Persist results), Control gate goes amber, **BLOCKED** badge stamps in, alert reads "Blocked — exception rate 47.2% exceeds the 5.0% control threshold". |
| 4 | 12.4–16.2 | **Nothing dropped** | "Exceptions (17)" cards cascade in (E001, E004, E007, E011, E014…). Caption: "Nothing silently dropped. / Every excluded row gets a rule, a cause, and a fix." |
| 5 | 16.2–19.6 | **AI narrates, Python counts** | AI Analysis card with the "Local LLM (Ollama, phi4-mini)" badge. The real narrative types out, and its numbers get a "✓ checked" tag. Caption: "The AI writes the words. / Python does the math." |
| 6 | 19.6–23.0 | **Outro** | Stat row: Customers 25 · Invoices 36 · Overdue 15 · Outstanding Rs 12,02,000.00, then the logo, name, stack, and `github.com/withrvr/collections-workflow`. |

## Sound
Synthesized in A minor at 112 BPM: a warm pad and a muted pluck arpeggio, with a soft kick that comes in at the reveal. The effects are tuned to the key: a pitched tick for each timeline stage, a low A thud plus a filtered noise hit for BLOCKED, and a soft rising swell into the outro. Effects sit about 8–10 dB under the music.
