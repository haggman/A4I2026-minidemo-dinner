# Dinner Scout on stage: the one-pager

Five minutes, coming back from a break. The page runs in Cloud Shell in your own project and opens in Chrome on
the laptop through Web Preview. Only Gemini and Google Maps cross the network. The script is in
`run-of-show/docs/TELEPROMPTER.md`.

## You need

- The laptop with Chrome, and **Location Services on for Google Chrome** (macOS System Settings ▸ Privacy &
  Security ▸ Location Services). Without it, the map starts at the city's landmark in `demo.env`.
- A handheld or lapel mic into the laptop, and the laptop's sound into the room. Laptop speakers feeding the
  laptop mic make the voice interrupt itself.
- **The fallback video on the laptop's disk** (see "Record the fallback" below). Wifi failure takes Cloud Shell
  down too, so the video can't live in the cloud.
- Your phone, to scan the QR code once in the morning.

## Once, the week before

```bash
gcloud config set project YOUR_PROJECT_ID
git clone https://github.com/haggman/A4I2026-minidemo-dinner.git && cd A4I2026-minidemo-dinner
bash scripts/make_places_key.sh && bash scripts/make_map_key.sh
bash scripts/start_demo.sh
```

The last command runs the pre-show check (about a minute), then starts the page. Then record the fallback.

## Morning of, at the venue, on the venue wifi

```bash
cd ~/A4I2026-minidemo-dinner && git pull && bash scripts/start_demo.sh
```

1. Read the last line of the check: **GO**, **GO WITH CARE** (slow: expect pauses) or **NO-GO** (use the video
   today, or fix the FAIL lines and run it again).
2. Click the `http://0.0.0.0:8080` link it prints. Chrome asks for the location: **Allow**. The top left should
   name a place at the venue.
3. Press **Start**, allow the microphone, and hold one short conversation at room volume through the room mic.
   Scan the QR code with your phone: Google Maps should open with directions.
4. Press **Stop**. Leave the Cloud Shell tab and the page open.

## At the break before the demo

```bash
bash scripts/start_demo.sh --quick
```

It restarts the page fresh in about 15 seconds and checks the voice is quick. Cloud Shell shuts down after 40
minutes without you touching it, so run this within 30 minutes of going on. Reload the page tab (View ▸ Reload
This Page). Leave it on the map; you press **Start** on stage.

## If it goes wrong

| What you see | What to do |
|---|---|
| She keeps interrupting herself | Press **Stop**, tick **Hold to talk**, press **Start**, then hold the **Hold to talk** button while you speak |
| Silence for more than 8 seconds | Ask "Are you still there?" If still nothing, press **Stop**, then **Start**, and say your line again |
| The map is in the wrong place | Say where you are: "I'm at the convention centre." The map moves |
| A list instead of a map | The page's map key isn't set or doesn't allow this address: `bash scripts/make_map_key.sh` (not mid-show: carry on with the list) |
| "Lost the connection to the server" | Press **Start** again. If the page won't load at all, it's the wifi or Cloud Shell: go to the video |
| No wifi, or Cloud Shell won't open | **The video.** New Chrome tab, File ▸ Open File…, pick the video, View ▸ Enter Full Screen, play. Say: "Conference wifi has opinions. Here's the one I recorded in rehearsal." |

To see what she heard, what was on screen and what the Scout reported: `tail -f ~/.a4i-dinner/server.log` in a
second Cloud Shell tab.

## Record the fallback

In rehearsal, after a GO:

1. On the page, before **Start**, press **Record** (bottom of the right column). Chrome asks what to share:
   choose **this tab** and press **Share**.
2. Press **Start** and run the demo the way the teleprompter says, start to finish.
3. Press **Stop recording**. The video lands in Downloads as `dinner-scout-DATE.mp4` (or `.webm`), with both
   voices: yours from the mic and hers from the page.
4. Play it back in Chrome (File ▸ Open File…) before you trust it. Keep the best one in a folder you'll find on
   the day, and copy it to a USB stick.

One good recording works in every city ("here's one from rehearsal"). Make a new one if you change the demo.

## After the show

Press **Stop** on the page, then `bash scripts/start_demo.sh --stop` in Cloud Shell.
