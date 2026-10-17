# Working agreement for this repo

This is a personal learning repo. The user learns by doing the steps in `WALKTHROUGH.md` and asking probing questions along the way. Keep these three files coherent:

- `STUDY_GUIDE.md` – the curriculum: scope, key questions, "done when". Changes rarely.
- `WALKTHROUGH.md` – the linear path with a **You are here** block at the top. One step per sitting, with exact commands and "look for" notes.
- `QUESTIONS.md` – log of probing questions, distilled answers, and what each changed.

## When the user asks a probing question
1. Answer it in chat.
2. Append the question, a distilled answer, and a **Changed** line to `QUESTIONS.md` under today's date.
3. If the answer changes what the next step should be, edit the affected step(s) in `WALKTHROUGH.md` and, if scope changed, `STUDY_GUIDE.md`.
4. Commit these together on `main` with a message starting `walkthrough:` or `questions:`.

## When the user reports finishing a step
1. Mark it `[x]`, add a row to the **Completed log** with a one-line takeaway, move **Now / Next / Last done**.
2. Tick the matching checkbox in `STUDY_GUIDE.md`.
3. Commit on `main`.

## When the user asks "what next" or "where am I"
Read the **You are here** block in `WALKTHROUGH.md` and answer from it. If the block is stale, fix it first.

## Conventions
- Work directly on `main`; no feature branches unless asked.
- Experiments live in `experiments/NN-name/`. Wire captures go in an `experiments/captures/` folder inside the experiment, annotated at the top.
- Steps in later parts of the walkthrough are deliberately coarse; expand a part into concrete steps when the user reaches it, not before.
- Origin uses the `github-aaronaston` SSH alias (personal account).
