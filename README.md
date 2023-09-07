A simple Python script which analyzes a holiday video, to remove audio tracks other than the
original language, and subtitles other than French.

Usage:
- The first argument must be the video file to process.
- The second argument can specify the output file.
- The third argument can specify the audio language (English if not given).
- The fourth and fifth arguments can specify the audio and subtitle tracks to keep.
- If not given, the fourth and fifth arguments will be guessed by parsing the mpv output.
