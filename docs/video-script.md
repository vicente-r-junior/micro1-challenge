# Solution video — the recording script

**Hard limit 5:00.**

## Read this rule once, then never worry about it again

**You speak only the text inside a box.** Everything else on this page is a
direction to you, and none of it is said out loud.

> Text in a box like this one is **spoken**. Read it word for word.

**DO** — a plain bold line like this is an **action**. Never spoken.

`# 4 · One real run` — headings are **labels
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
| **Terminal** | cleared, in the repo root | scene 10 only |
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
- [ ] Browser is the **only** window you share until scene 10
- [ ] Run `rm -f /tmp/demo_fastapi.py` **before recording** — scene 10 proves
      the file is *not* created, and a leftover from a rehearsal contradicts you
- [ ] Dry-run scene 10 once. Verified working today: with `n` it prints
      `not written (approval declined)`, and `ls` then says `No such file`

## How to sound senior

Not vocabulary — choices. Four habits:

1. **Lead with the decision, not the feature.** The script already does this.
2. **Say a trade-off out loud.** Scene 6 is one.
3. **Name the limit before they find it.** Scene 8.
4. **Never narrate the screen.** Do not say "here I click". Say what it means.

No apologising. No "I tried to". No "I hope". State what you measured.

**Your accent is not being scored. Clarity is.** No sentence below is longer
than twelve words; the average is five. Stop at every full stop — a real pause
reads as confidence, rushing reads as nerves.

---

> **How this works now.** One window: the report page, scrolled top to bottom in
> its own order. You never switch apps until the very last scene. Every scene is
> **scroll to the heading, stop, then talk** — never scroll and talk at once.
>
> The page's own navigation bar is your running order:
> **Measurements → Mechanism → Agent → Results → Changelog → Limits**.
> If you lose your place, click the next name in that bar.

---

# 1 · Open · camera, no screen yet · 16 words

> Hi, I am Vicente. I built an agent that migrates Flask to FastAPI.
>
> The hard part was never writing the new code.

---

# 2 · Measurements · 45 words

**DO** — Share the browser. Page at the **very top**. Then talk.

> A model rewrites a Flask service in eight seconds. That part is easy.
>
> Proving the new one behaves the same is the part that stops teams.

**DO** — Scroll to the grid. **Stop scrolling.** Then talk.

> Each cell is one request, sent to both apps. Green means the same answer.
>
> I wrote fourteen cases. A model passed eleven.

**DO** — Cursor on the two rows marked **REAL**. Then talk.

> These two are not mine. Real open-source code. Zero out of two.

---

# 3 · What it broke · 38 words

**DO** — Click **Mechanism** in the nav, or scroll to *"The regressions that
matter are not crashes"*. Stop. Then talk.

> None of it was a crash. The app started, and it lied.

**DO** — Cursor on the **last row of that table**. **Wait two seconds.** Then talk.

> Here the old app had a bug. It returned five hundred.
>
> The migration fixed it. Now it returns four zero four.
>
> Better code. Different contract. Every client that retries on five hundred breaks tomorrow.

---

# 4 · One real run · 40 words

**DO** — Click **Agent** in the nav. Stop at *"One repair, turn by turn"*. Then talk.

> One real run, start to finish.
>
> The old app wants a token. Without one, four zero one.
>
> The migration answered five hundred. The guard broke.
>
> The agent read the three that failed, wrote a fix, tested again.
>
> Fourteen out of fourteen.

---

# 5 · Baseline, and advanced · 40 words

**DO** — Click **Results**. Stop at the baseline/advanced table. Then talk.

> The baseline is one prompt. Twelve out of sixteen, and zero on real code.
>
> The advanced one is the same model, with a repair loop.
>
> Sixteen out of sixteen. Two out of two on real code.

**DO** — Scroll back up to the grid. Set **gpt-5.5** and **"one prompt"** — 44 red
cells. Click **"+ repair loop"**. **Say nothing for two seconds.**

> That is the repair loop. The change that mattered most.

---

# 6 · Models, and what I removed · 34 words

**DO** — Click the models across the top, slowly. Then talk.

> Does a better model fix it? Five models, two companies. Thirteen tries on real
> code, and zero passed.

**DO** — Scroll to *"Two components were removed"*. Stop. Then talk.

> Two parts of my agent did not pay for themselves. Sixty percent more cost, zero
> more results. So I removed both.

---

# 7 · Changelog · 16 words

**DO** — Click **Changelog** in the nav. Stop. Then talk.

> Seventeen times my own harness was wrong. Every entry here is a number I
> believed, and should not have.

---

# 8 · The limit · 12 words

**DO** — Click **Limits**. Stop. Then talk.

> One limit. The old app has to run. If it needs a database, I record nothing.

---

# 9 · The take · 42 words

**DO** — Camera, or leave the page still. Slow right down.

> The easy answer is to let a model write the tests.
>
> But those tests come from the new code.
>
> It renamed "error" to "detail". So the test checks "detail". Green.
>
> The test and the code make the same mistake, together.
>
> My rule: a verifier needs truth from something the agent cannot change.
>
> Here that was easy. The old app is still running, and it answers everything.

---

# 10 · One thing, live · 18 words

**DO** — Switch to the **Terminal**, already open and cleared. Paste:

```bash
python src/migrate.py data/cases/case_14_restful_todo_simple/legacy_app.py --out /tmp/demo_fastapi.py --replay --no-memory
```

**DO** — Let it finish. Then talk.

> Last thing. Before it writes anything, it asks me.

**DO** — Type **`n`**, Enter. Then paste:

```bash
ls /tmp/demo_fastapi.py
```

> I said no. Nothing was written.

**DO** — One beat. Then, flat and short:

> Thank you for watching.

---

# Timing — do this once before you record

The first two attempts ran long. That was the script's fault twice over: it was
sized at 145 words a minute against your measured **81**, and it made you switch
windows and point at things while talking. Both are gone.

This version is **374 spoken words** and one window. At 81 words a minute that is
4:37, which leaves only about twenty seconds for scrolling. **But 81 was measured
on the old script** — long sentences, four apps, pointing mid-sentence. Those are
exactly what slows a reader down in a second language. Short lines and "stop,
then talk" should put you nearer 95, which is 3:56 and comfortable.

You do not have to guess. Measure it.

## The two-minute test

Stopwatch, out loud, camera pace. **Read scenes 1 to 4. Nothing else.** That is
169 words.

| Your time | What to do |
|---|---|
| under **1:50** | record as written, you have real margin |
| **1:50 – 2:10** | make **cut A**, then record |
| over **2:10** | make **cut A and cut B**, then record |

## The two cuts, in order

**Cut A — scene 8, the limit.** Delete the whole scene, all sixteen words. The
brief does not require it and the report page carries it in writing. **Saves ~12 s.**

**Cut B — scene 6, the first line.** Delete:

> Does a better model fix it? Five models, two companies.

Keep *"Thirteen tries on real code, and zero passed."* You lose the setup, not
the evidence. **Saves ~7 s.**

## Never cut these

Scenes 4, 5, 6's second half, 7, 9, and 10.

The brief names seven things the video must contain: the problem, the baseline,
one execution end to end, the final comparison, the changelog, the change that
mattered most, and the experiment you removed. Scene 4 is the execution. Scene 5
is the baseline against the advanced solution *and* the change that mattered.
Scene 6 is the removed experiment. Scene 7 is the changelog. Scene 9 is the
insight the whole project is built on, and scene 10 is the human-approval ground
rule.

## Three rules for the take

**Stop, then talk.** Every scene says it. Scroll to the heading, let the page
settle, take a breath, then speak. A judge watching a still page while you
explain it looks deliberate. A judge watching you scroll and talk looks lost.

**Never fix an overrun by speaking faster.** Speed is the first thing that makes
an accent hard to follow, and a judge working to understand you stops hearing the
argument. If you are long, cut.

**If you lose your place, use the nav bar.** Measurements, Mechanism, Agent,
Results, Changelog, Limits — that is the running order, it is on screen the whole
time, and clicking it looks like navigation rather than rescue.

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
- [ ] One execution, uncut (scene 4)
- [ ] The approval gate refusing the write (scene 5)
- [ ] Comparison grid on screen (scene 6)
- [ ] The change that mattered most, said out loud (scene 6)
- [ ] The removed experiment, said out loud (scene 6)
- [ ] The changelog, on screen and explained (scene 6)
- [ ] The limitation, volunteered (scene 8)
- [ ] The hot take (scene 9)
- [ ] Terminal readable at laptop size
- [ ] Audio clear, no room echo
