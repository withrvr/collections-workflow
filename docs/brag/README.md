# Launch video

`brag.mp4` is a 23-second launch video for this project (1920×1080, 30fps, with sound). It was made with [`/brag`](https://github.com/latent-spaces/brag), specifically its `/brag-slim` workflow. `brag.jpg` is its poster frame and is also baked in as frame 0. `share-copy.txt` is a caption you can post as-is, and `brag-plan.md` is the storyboard.

Every figure on screen comes from the sample workbook
(`backend/app/collections/fixtures/dataset_a_original.xlsx`) and the app's own output for it:

- 36 invoices and 17 exception rows
- a 47.2% exception rate, so the run is blocked
- Rs 12,02,000.00 overdue
- the real exception messages
- the real AI narrative

The UI is redrawn from the real components, using the same copy, colours and logo.

## Rebuild it

`source/` holds everything needed to re-render the video:

- `brag.html` draws each frame as a pure function of time.
- `capture.js` captures the frames with Playwright and Chromium.
- `audio.py` synthesizes the music and sound effects with numpy.

```bash
cd docs/brag/source
node capture.js stills 3.6 9.6 22.0        # spot-check stills -> stills/
node capture.js video                      # all frames -> video-noaudio.mp4
python3 audio.py                           # soundtrack -> music.wav
node capture.js stills 22.0 && cp stills/t-22.00.png poster.png
ffmpeg -y -i video-noaudio.mp4 -loop 1 -i poster.png -i music.wav \
  -filter_complex "[0:v][1:v]overlay=0:0:enable='eq(n,0)':shortest=1,format=yuv420p[v];[2:a]loudnorm=I=-16:TP=-1.5:LRA=7[a]" \
  -map "[v]" -map "[a]" -c:v libx264 -preset slow -crf 20 -c:a aac -b:a 192k \
  -movflags +faststart -t 23 ../brag.mp4
ffmpeg -y -i poster.png -q:v 2 ../brag.jpg
```

`capture.js` loads Playwright from the global install at `/opt/node22/lib/node_modules/playwright`. If yours is somewhere else, change that path. The rebuild needs Node 22+, FFmpeg, Python 3 with numpy, and the Inter font.
