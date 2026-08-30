# Solution video — the recording script

**Hard limit 5:00.**

## Read this rule once, then never worry about it again

**You speak only the text inside a box.** Everything else on this page is a
direction to you, and none of it is said out loud.

> Text in a box like this one is **spoken**. Read it word for word.

**DO** — a plain bold line like this is an **action**. Never spoken.

`# Block 4 — why a model cannot check a model · 20 s` — headings are **labels
for you**, so you can find your place. Never spoken. Neither is the duration.

There is no transition to say between blocks. The cut *is* the transition.

Work top to bottom. Each block is one take. If a block goes wrong, redo only
that block.

**Calibrate before you record — do not trust my estimate.**

Read every boxed line aloud, top to bottom, at the pace you actually plan to
speak, and time it. Then:

| Your read-through | What to do |
|---|---|
| **under 4:20** | You are fine. Record as written. |
| **4:20 – 4:40** | Fine, but keep the on-screen pauses tight. |
| **over 4:40** | Apply the cut list near the bottom, in order, until you are under 4:30. |

The gap between your read-through and 5:00 is for silence: the grid animating,
the terminal running, you typing `n` and `y`. Budget about **twenty seconds**
for all of it.

Do not improvise extra sentences, and never fix an overrun by speeding up. A
rushed video reads worse than a short one.

---

# Before you press record

## Your two screens

**Screen A — the one you share and record.** Three windows, nothing else. No
Slack, no notifications, no personal tabs.

| Window | What is open | Used in |
|---|---|---|
| **VS Code** | `data/cases/case_14_restful_todo_simple/legacy_app.py` | Block 1 |
| **Browser** | `docs/index.html`, scrolled to the top | Blocks 2, 3, 6 |
| **Terminal** | in the repo root, font at 18–20pt | Blocks 4, 5 |

Both terminal commands are long. **Paste them, do not type them** — have them
ready in a scratch file, or press Up-arrow if you ran them while rehearsing.

**Screen B — for your eyes only.** This document, at eye level, as close to the
webcam as you can put it. If you look *down* to read, the camera sees it. If it
sits beside the lens, you look like you are thinking.

## Switching windows without looking clumsy

On macOS, put each window in its own Space and switch with **Ctrl + ←/→**. It
slides instead of flashing, and you never pick the wrong window by accident.
Practise the three switches twice before recording.

If you would rather not use Spaces, arrange the three windows so `Cmd + Tab`
goes Browser → VS Code → Terminal in that order.

## Setup checklist

- [ ] Terminal font **18–20pt** — a judge on a laptop must read the diff
- [ ] Recording **1080p**, not 4K
- [ ] Do Not Disturb on
- [ ] Only Screen A is being captured
- [ ] Run `make reproduce` once beforehand so Docker is warm
- [ ] Browser zoom at 100%, page scrolled to the very top

## How to sound senior

Not vocabulary — choices. Four habits:

1. **Lead with the decision, not the feature.** The script already does this.
2. **Say a trade-off out loud.** Block 7 has one.
3. **Name the limit before they find it.** Block 8.
4. **Never narrate the screen.** Do not say "here I click". Say what it means.

No apologising. No "I tried to". No "I hope". State what you measured.

**Your accent is not being scored. Clarity is.** No sentence below is longer
than twelve words; the average is five. Stop at every full stop — a real pause
reads as confidence, rushing reads as nerves.

---

# Block 0 — the open · 8 s

**DO** — Camera only. No screen share yet.

> Hi, I am Vicente. I built a migration agent, Flask to FastAPI.
>
> I will be moving between a report, some code, and a terminal.
>
> So let me start with the problem.

**Do not** thank anyone here. The sign-off is at the very end, in Block 8.

---

# Block 1 — the problem · 28 s

**DO** — Switch to **VS Code**, showing
`data/cases/case_14_restful_todo_simple/legacy_app.py`.

> So this is a Flask service, and it runs in production.
>
> The team wants FastAPI. They have wanted that for two years.
>
> But writing the new code is easy. A model does it in eight seconds.
>
> The real problem is proof. Nobody can prove the new app behaves the same.
>
> And the old one is what every client was built on.

---

# Block 2 — how I measure it · 45 s

**DO** — Switch to the **Browser**. Click **Measurements**. Set the controls to
**"one prompt"** and **gpt-5.5**.

> So how do you know if a migration is correct? This is how I measure it.
>
> Each green cell is one HTTP request, sent to both apps. Green means: same answer.
>
> Now, I wrote fourteen test cases. Each one is a trap I knew about.
>
> And a modern model passed eleven. So by my benchmark, it looks fine.

**DO** — Move the cursor to the two rows tagged **REAL** (13 and 14). Leave it
there.

> But these two are not mine. This is real open-source code.
>
> And it is zero out of two.

---

# Block 3 — what it broke · 35 s

**DO** — Same page. Scroll to the section *"The regressions that matter are not
crashes"*.

> So what did it break? Three things, and none is a crash.
>
> One route just disappeared. It answered two hundred. Now, four zero five.
>
> Every error message changed shape. But my favourite is this one.

**DO** — Cursor on the **last row**. **Pause two seconds.**

> The old app had a bug here. It returned five hundred.
>
> And the migration fixed it. Now it returns a clean four zero four.
>
> So, better code. But a different contract.
>
> Because every client that retries on five hundred breaks tomorrow.

---

# Block 4 — one real run · 45 s

**DO** — Switch to the **Terminal**. Paste:

```bash
python src/show_trajectory.py trajectories/cross_model/v2_repair/case_02_blueprint_auth.jsonl --compact
```

**DO** — 19 coloured lines, one screen. There are only **three** things to point
at, in this order:

1. the yellow **★ FIRST DIFFERENTIAL** — 11 out of 14
2. the three **legacy 401 … got 500** lines
3. the green **parity 100%**

> Now let me show you the agent working. This is one real run.
>
> The old app protects these routes. No token, and it answers four zero one.

**DO** — Point at the three probe lines. **Pause two seconds.**

> But the migration answers five hundred. The guard broke.
>
> So the agent opens the three requests that failed, and reads both answers.
>
> Then it writes a fix, and runs the whole thing again before handing it over.

**DO** — Point at the green `parity 100%`.

> Fourteen out of fourteen. And nothing here was scripted by me.
>
> I only told it: eight turns, and three tries.

**DO** — Point at the last line, `⏸ HUMAN [auto] answered '(not asked)'`.

> One thing though. This run was the benchmark, so nobody was asked.
>
> Let me show you what happens when someone is.

---

# Block 5 — the human in the loop · 25 s

**DO** — Back to the **Terminal**. Clear the stale file first, or the demo lies:

```bash
rm -f /tmp/demo_fastapi.py
```

**DO** — Then paste:

```bash
python src/migrate.py data/cases/case_14_restful_todo_simple/legacy_app.py --out /tmp/demo_fastapi.py --replay --no-memory
```

> Now, the part I care most about. The human in the loop.
>
> So before writing anything to disk, it asks me.

**DO** — Type **`n`**, Enter. Then:

```bash
ls /tmp/demo_fastapi.py
```

> I say no. And nothing was written.

**DO** — Same migrate command again. Type **`y`**. Then:

```bash
ls -la /tmp/demo_fastapi.py
```

> Now I say yes. And there it is.

---

# Block 6 — does it work? · 60 s

**DO** — Switch to the **Browser**. Click **Measurements**. Model on
**gpt-5.5**, configuration on **"one prompt"** — 44 red cells on screen.

> Okay, so, does this actually work?

**DO** — Click **"+ repair loop"**. **Say nothing for two seconds** while the 44
red cells turn green.

> That is the repair loop. The change that mattered most.

**DO** — Click through the models, slowly: **gpt-4o-mini → gpt-5.4-mini →
ds-v4-pro**.

> So, does a better model fix this? I ran the baseline seven times.
>
> Five models, two companies. The score moves a lot, from one up to twelve.
>
> But thirteen tries on real code, and zero passed. Every model.
>
> So a better model is not the fix.

**DO** — Click **Results**, scroll to the table headed *"Two components were
removed"*.

> And two parts of my agent did not pay for themselves.
>
> The analyst and the memory. Sixty percent more cost, zero more results.
>
> So I measured both, and I removed both.

---

# Block 7 — where it fails · 25 s

**DO** — Look at the **camera**.

> Now, where does this not work?
>
> It has to run the old app. I tried a real file, one thousand lines.
>
> It found thirty-nine routes, and recorded nothing. That file needs a database.
>
> No running app, no truth. So this works best on simple code.

---

# Block 8 — the take, and out · 35 s

**DO** — Camera. Slow right down. This is the ending.

> So, what did I learn?
>
> The easy answer is to let a model write the tests.
>
> But those tests come from the new code. They check what the code decided.
>
> It changed "error" to "detail". So the test checks "detail". Green.
>
> Actually, the test and the code make the same mistake together.
>
> So, my rule. A verifier gets its truth from something the agent cannot change.
>
> And here that was easy. The old system is still running, and it answers everything.

**DO** — One beat of silence. Then, flat and short:

> Thank you for watching.

---

# If you run over five minutes

**Time your read-through first**, then cut from this list in order until you are
under 4:35. Each cut is exact — delete the boxed lines named, nothing else.

| # | Cut | Saves | What you lose |
|---|---|---|---|
| 1 | **Block 7** entirely — *"Now, where does this not work?"* to *"…best on simple code"* | **~22 s** | The limitation. Volunteering it is a strong signal, so cut this only if you must. The README carries it. |
| 2 | **Block 3**, the line *"Every error message changed shape. But my favourite is this one."* | **~6 s** | One finding. Keep the five-hundred story after it; that is the best moment. |
| 3 | **Block 8**, the two lines about `"error"` and `"detail"` | **~12 s** | Detail on the hot take. The rule that follows still lands. |
| 4 | **Block 0**, *"I will be moving between a report, some code, and a terminal."* | **~5 s** | A small courtesy. |

**Never cut Block 4, Block 5, or the last three lines of Block 8.** The brief
requires a full execution and the removed experiment; the approval gate is the
ground rule on human oversight; and the closing rule is the insight the whole
project is built on.

**Never fix an overrun by speaking faster.** Speed is the first thing that makes
an accent hard to follow.

# Words to practise

| Word | Say it like |
|---|---|
| behaviour | bi-HEY-vior |
| parity | PA-ri-ti |
| migration | my-GREY-shun |
| legacy | LE-ga-si |
| spec | spek |
| probe | prohb |
| route | root |
| harness | HAR-nes |

| Written | Say |
|---|---|
| 12/16 | twelve out of sixteen |
| 0/2 | zero out of two |
| 405 | four zero five |
| 500 | five hundred |
| 100% | one hundred percent |

---

# Before you upload

- [ ] Under 5:00
- [ ] The baseline shown **and** its silent regression shown
- [ ] One execution, uncut (Block 5)
- [ ] The approval gate: `n` then `y` (Block 6)
- [ ] Comparison table on screen (Block 7)
- [ ] The change that mattered most, said out loud (Block 7)
- [ ] The removed experiment, said out loud (Block 7)
- [ ] The limitation, volunteered (Block 8)
- [ ] Terminal readable at laptop size
- [ ] Audio clear, no room echo
