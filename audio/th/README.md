# Bundled Thai speech

Generated once locally using **FastThaiG2P v0.3.0 Thai-finetuned Kokoro-82M**, voice `thai_som`. No paid speech service was used. These MP3 files are served by this repository's GitHub Pages site. Playback does not contact a TTS provider, require a key, use an installed Thai voice, or download model weights. Normal website bandwidth/hosting limits still apply. An initial connection is required to load the site and files; this is not an offline PWA.

Model and runtime source:
- https://github.com/awslabs/FastThaiG2P (source revision `c4759eef7df03e11fcbb9aa83efe8cf21709fd2f`)
- https://github.com/awslabs/FastThaiG2P/releases/tag/v0.3.0
- https://github.com/cstorm125/kukuru-tts
- https://github.com/hexgrad/kokoro

Upstream source is Apache-2.0. See the accompanying license copy. Only generated audio, its manifest and the small playback adapter are shipped to browsers; no model weights or upstream runtime code are included in the website. Manifest records generation text, SHA-256 and duration for every clip, and upstream model asset SHA-256 values verified against the release metadata.

Rebuild (development machine only): install Python 3.11+, FFmpeg, `onnxruntime` and FastThaiG2P from the pinned source revision. Download `kokoro_thai.onnx`, `thai_som.npy` and `config.json` from the release above to one directory. Run:

```
PYTHAINLP_DATA=/tmp/kfma-pythainlp-data python tools/generate_thai_audio.py /path/to/model-directory
```

The script verifies all three model file checksums and creates missing clips. To replace a clip after editing its text, delete only that clip and rerun. Review pronunciation and pacing before classroom use, especially at high display speeds: the existing game schedule remains unchanged, so a new number can interrupt an earlier sound.

Coverage: full clips for 0–99; Thai place-value units through แสน; เอ็ด; ลบ/บวก; all existing Thai sample messages and split prefixes/suffixes for question numbers, answers and the round summary. Number composition supports integers from -999999 to 999999, covering the game's largest possible sum (99 × 9999 = 989901). Arbitrary new Thai sentences require a new generated clip; this is not unrestricted runtime TTS.
