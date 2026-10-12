# Plan: Dinner Scout's run-of-show

**Written 2026-10-12, for Patrick's run-through.** The scripted version is in `docs/` (built from `src/content.js`).

## What the demo is for

A five-minute energiser coming back from a break, at each of the four events. A product showcase, not architecture:
you ask a voice agent out loud for dinner near the venue, it narrows it down with you, and it ends on a QR code the
room can scan. Everyone has had the problem; nobody needs to know what an agent is to get it.

## Decisions

- **No deck, no slide numbers.** Each teleprompter page leads with the tab to be on, like the kickoff's.
- **Two kinds of line:** orange SPEAK lines are said to Dinner Scout; teal SAY lines are said to the room.
- **Everything live.** No replay mode on the page: a voice conversation is the point. The backup is a **video of a
  good run** recorded in rehearsal with the page's own **Record** button, kept on the laptop and open in a second
  tab (wifi failure takes Cloud Shell down too).
- **One start block:** `bash scripts/start_demo.sh` runs the pre-show check and starts the page; `--quick` at the
  break restarts it and re-checks the voice inside Cloud Shell's 40-minute idle limit.
- **Four core beats, two optional:** ask · interrupt and narrow · the wheelchair question · pick and scan; optional:
  another city next week, another language. Core total about 4.25 minutes.

## The pages

| # | Tab | The beat | Min |
|---|---|---|---|
| — | Cloud Shell | Before the show: once, morning of, at the break | — |
| 1 | Dinner Scout page | Ask for dinner, out loud: here or elsewhere, walk, how far | 1.5 |
| 2 | Dinner Scout page | Interrupt ("no chains"), then quiet and open now | 1 |
| 3 | Dinner Scout page | My colleague uses a wheelchair: which of these works? | 0.75 |
| 4 | Dinner Scout page | Optional: New York next week, near Chelsea Market | 0.5 |
| 5 | Dinner Scout page | Optional: carry on in Spanish | 0.5 |
| 6 | Dinner Scout page | Number one: route, QR code, scan; the closing line | 1 |
| 7 | Fallback video tab | Only if the wifi fails | — |

## Still to confirm in the run-through

Listed at the end of the planning guide (`GUIDE.confirm` in `src/content.js`): the Record button in real Chrome,
the venue location, the interruption through a room mic, the "no chains" path, Spanish, the next-week city, and the
QR code on iPhone and Android.
