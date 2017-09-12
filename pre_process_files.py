"""
Preprocess Module
- Converts every AudioFile into wav files with ffmpeg
- Normalizes the Sampling rate
- Normalizes volume levels
- Trims files that are too long
- Trim beginning and end of files
- Augments dataset by generating combinations of speech noise
"""
