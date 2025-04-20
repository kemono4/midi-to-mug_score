# midi-to-mug_score

## Rhythm Game
A simple rhythm game built with Pygame.  
It supports parsing MIDI files and converting them into playable charts.

### Features
- 🎵 Load and play MIDI files
- 🎹 7-key mode based on scale degrees (Do -> 1, Re ->2, Mi -> 3...)
- 🎯 Judgement system: PERFECT / GOOD / OK / MISS
- 📊 Score, combo, and accuracy calculation

#### TBD
- GUI for selecting song and hi-speed
- Save data to JSON for faster load and local record
- Auto chord accompaniment (Best for Monophonic MIDI track)

### Requirements
- Python 3.8+
- [pygame](https://www.pygame.org/)
- [music21](https://web.mit.edu/music21/)

Install dependencies with:
```bash
pip install pygame music21
```
