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
- [ ] Terminal **at least 40 rows tall** — Block 4 prints 34 lines and must not
      scroll
- [ ] `rm -f /tmp/demo_fastapi.py` — Block 5 proves the file is *not* created,
      which fails if one is left over from a rehearsal
- [ ] Dry-run both terminal commands once. Both were verified working today:
      Block 4 prints 34 lines ending in `parity 100%`, and Block 5 with `n`
      prints `not written (approval declined)` and then `No such file`

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

# Block 0 — the open · 15 s

**DO** — Camera only. No screen share yet.

> Hi, I am Vicente. I built an agent that migrates Flask to FastAPI.
>
> Let me start with the problem.

**Do not** thank anyone here. The sign-off is the last line of Block 8.

---

# Block 1 — the problem · 35 s

**DO** — Switch to **VS Code**, showing
`data/cases/case_14_restful_todo_simple/legacy_app.py`.

> This is a Flask service. It runs in production.
>
> The team wants FastAPI. Writing the new code is easy.
>
> A model does it in eight seconds.
>
> The hard part is proof. Nobody can prove the new app behaves the same.
>
> And the old one is what every client was built on.

---

# Block 2 — how I measure it · 40 s

**DO** — Switch to the **Browser**. Click **Measurements**. Controls on
**"one prompt"** and **gpt-5.5**.

> How do I know a migration is correct?
>
> Each green cell is one request, sent to both apps. Green means the same answer.
>
> I wrote fourteen test cases. A modern model passed eleven.

**DO** — Cursor on the two rows tagged **REAL**. Leave it there. *Then* speak.

> These two are not mine. This is real open-source code.
>
> Zero out of two.

---

# Block 3 — what it broke · 40 s

**DO** — Same page. Scroll to *"The regressions that matter are not crashes"*.

> So what broke? None of it is a crash.
>
> One route disappeared. Every error message changed shape.
>
> But this one is my favourite.

**DO** — Cursor on the **last row**. **Pause two seconds.** *Then* speak.

> The old app had a bug. It returned five hundred.
>
> The migration fixed it. Now it says four zero four.
>
> Better code. Different contract.
>
> Because every client that retries on five hundred breaks tomorrow.

---

# Block 4 — one real run · 40 s

**DO** — Switch to the **Terminal**. Paste, and **say nothing while it prints**:

```bash
python src/show_trajectory.py trajectories/cross_model/v2_repair/case_02_blueprint_auth.jsonl --compact
```

**DO** — Hands off the mouse. Just read. The judge can see the screen.

> This is one real run.
>
> The old app wants a token. Without one, it answers four zero one.
>
> The migration answered five hundred. So the guard broke.
>
> The agent read the three requests that failed. It wrote a fix, and tested again.

**DO** — *Now* point at the green `parity 100%`. **One gesture, and that is the
only one in this block.**

> Fourteen out of fourteen. I only told it: eight turns.

---

# Block 5 — the human in the loop · 25 s

**DO** — Clear the stale file first, or the demo lies:

```bash
rm -f /tmp/demo_fastapi.py
```

**DO** — Then paste:

```bash
python src/migrate.py data/cases/case_14_restful_todo_simple/legacy_app.py --out /tmp/demo_fastapi.py --replay --no-memory
```

> Before it writes anything, it asks me.

**DO** — Type **`n`**, Enter. Then:

```bash
ls /tmp/demo_fastapi.py
```

> I said no. And nothing was written.

---

# Block 6 — does it work? · 60 s

**DO** — Browser. **Measurements**. **gpt-5.5**, **"one prompt"** — 44 red cells.

> Does this actually work?

**DO** — Click **"+ repair loop"**. **Say nothing for two seconds** while the 44
red cells turn green.

> That is the repair loop. The change that mattered most.

**DO** — Click through the models: **gpt-4o-mini → gpt-5.4-mini → ds-v4-pro**.

> Does a better model fix it? I ran the baseline seven times.
>
> Five models, two companies. Thirteen tries on real code. Zero passed.

**DO** — Click **Results**, scroll to *"Two components were removed"*.

> And two parts of my agent did not pay for themselves.
>
> Sixty percent more cost. Zero more results. So I removed both.

**DO** — VS Code. Open **`CHANGELOG.md`**. Scroll fast, top to bottom.

> It is all in the changelog. Seventeen times I got the harness wrong.

**DO** — Camera.

> One limit. The old app has to run. If it needs a database, I record nothing.

---

# Block 8 — the take, and out · 55 s

**DO** — Camera. Slow right down. This is the ending.

> The easy answer is to let a model write the tests.
>
> But those tests come from the new code.
>
> It renamed "error" to "detail". So the test checks "detail". Green.
>
> The test and the code make the same mistake, together.
>
> So, my rule. A verifier needs its truth from something the agent cannot change.
>
> Here that was easy. The old app is still running, and it answers everything.

**DO** — One beat of silence. Then, flat and short:

> Thank you for watching.

---

# Timing — read this before you record again

The first attempt ran long, and that was a fault in the script, not in you. It
was written at 145 words a minute. **You read at 81** — measured from your own
run: 244 words in about three minutes, pauses and clicks included. At that pace
the old script was 7:50. It was never going to fit.

This version is **400 words**, and its sentences are much shorter, which is what
actually costs time — a long sentence in a second language is where you stop and
restart. Short lines should carry you faster than 81.

## The ninety-second test

Do this once before recording. Stopwatch, out loud, at the pace you would use on
camera:

**Read Blocks 0 to 3. Nothing else.** That is 174 words.

| Your time | What it means | What to do |
|---|---|---|
| under **1:50** | you are at 95+ wpm | record the script as written, you have margin |
| **1:50 – 2:10** | you are near 85 wpm | make **cut A** below, then record |
| over **2:10** | still around 80 | make **cut A and cut B**, then record |

The test is the whole point: it tells you before you press record, instead of
you finding out at Block 4 with two minutes left.

## The two cuts, in order

**Cut A — Block 6, the models line.** Delete:

> Does a better model fix it? I ran the baseline seven times.

Keep the line after it. You lose the setup, not the evidence. **Saves ~9 s.**

**Cut B — Block 3, the two middle findings.** Delete:

> One route disappeared. Every error message changed shape.

Go straight from *"None of it is a crash"* to *"But this one is my favourite"*.
The five-hundred story is the best moment in the video and it survives intact.
**Saves ~8 s.**

## Never cut these

Block 4, Block 5, any of Block 6, and the last four lines of Block 8.

The brief names seven things the video must contain: the problem, the baseline,
one execution end to end, the final comparison, the changelog, the change that
mattered most, and the experiment you removed. Block 6 alone holds four of them.
Block 5 is the human-approval ground rule. Block 8 is the insight the whole
project is built on.

## Two rules for the take itself

**Never fix an overrun by speaking faster.** Speed is the first thing that makes
an accent hard to follow, and a judge who has to work to understand you stops
hearing the argument.

**Never point and speak at the same time.** That is what made Block 4 hard. Every
block now separates them: the **DO** happens, *then* you talk, or you talk and
*then* point. Block 4 has exactly one gesture in it now, and it comes after the
sentence is finished.

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
