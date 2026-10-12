# run-of-show/—how Dinner Scout is presented

Dinner Scout is a **five-minute spoken conversation** with a voice agent, no deck, ending on a QR code the room can
scan. This folder is the script. The one-pager for the day is [`../STAGE.md`](../STAGE.md).

| File | What it is |
|---|---|
| [`docs/TELEPROMPTER.md`](docs/TELEPROMPTER.md) | Before the show (once, morning of, at the break), then one beat per page: the tab, what to say to her, what a good answer looks like, what to do if it goes wrong |
| `docs/TELEPROMPTER - Dinner Scout.docx` | The same, for a second monitor |
| [`docs/PLANNING-GUIDE.md`](docs/PLANNING-GUIDE.md) | The night-before document: how it works, setup, recording the fallback, the talk track, a fact sheet |
| `docs/PLANNING GUIDE - Dinner Scout.docx` | The same, in Word |
| [`PLAN.md`](PLAN.md) | Why the demo is shaped this way |
| `src/content.js` | The one source all four documents are built from |

## Run it

```bash
bash scripts/start_demo.sh          # from the repo root in Cloud Shell: the pre-show check, then the page on port 8080
```

## Rebuild the documents

```bash
cd run-of-show && npm install && bash src/build.sh
```

Edit `src/content.js`, never the generated files in `docs/`. The renderers come from the demo-pack starter kit.
