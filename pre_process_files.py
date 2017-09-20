"""
Preprocess Module
- Converts every AudioFile into wav files with ffmpeg
- Normalizes the Sampling rate
- Normalizes volume levels
- TODO: Trims files that are too long
- TODO: Trim beginning and end of files
- Augments dataset by generating combinations of speech noise
"""
import numpy as np
import os
import random
import scipy.io.wavfile as wav
import shutil
import subprocess

import logging_setup

logger = logging_setup.setup_logger("Preprocess Module")

THREADS = 4
NUM_AUGMENT = 20  # The number of files to generate by augmenting the noise with clean audio
SAMPLE_RATE = 44100
VALID_AUDIO = ["mp3", "aac", "mp4", "ogg", "wav", "opus"]


def format_int(number):
    assert type(number) is int
    global prefix_size
    return f"{number:0{prefix_size}d}"


def is_audio_file(file_name):
    return file_name.split(".")[-1].lower() in VALID_AUDIO


def make_dir(dir_path):
    if os.path.exists(dir_path) and os.path.isdir(dir_path):
        return
    elif not os.path.exists(dir_path):
        os.mkdir(dir_path)
    else:
        raise Exception(f"\"{dir_path}\" exists but is not a directory")


def set_prefix_size(clean_dir, dirty_dir):
    """Set the prefix size according to the maximum # of files"""
    num_clean = len(os.listdir(clean_dir))
    num_dirty = len(os.listdir(dirty_dir))
    num_dirty += min(NUM_AUGMENT, num_clean, num_dirty)
    global prefix_size
    prefix_size = len(str(max(num_clean, num_dirty)))


def merge_channels(in_dir, out_dir):
    """Merge stereo channels into mono channels and normalize the sampling rate"""
    logger.info("Merging audio channels into mono...")
    make_dir(out_dir)
    files = os.listdir(in_dir)
    for idx, file in enumerate(files):
        if is_audio_file(file):
            logger.debug(f"Merging audio channels in file \"{file}\"...")
            in_path = os.path.join(in_dir, file)
            file_name = format_int(idx) + "_" + "".join(file.split(".")[:-1]) + ".wav"
            file_name = file_name.replace(" ", "_")
            file_name = file_name.replace("-_", "_")
            out_path = os.path.join(out_dir, file_name)
            subprocess.run(["ffmpeg",
                            "-i", in_path,
                            "-loglevel", "panic",
                            "-ac", "1",  # Merge into 1 mono channel
                            "-ar", str(SAMPLE_RATE),
                            "-threads", str(THREADS),
                            out_path])
    logger.info("Finished merging audio channels into mono")


def normalize_volume(in_dir, out_dir):
    """Normalize the audio volume levels"""
    logger.info("Normalizing volume levels...")
    make_dir(out_dir)
    for idx, file in enumerate(os.listdir(in_dir)):
        logger.debug(f"Normalizing volume level of file \"{file}\"...")
        in_path = os.path.join(in_dir, file)
        subprocess.run(["ffmpeg-normalize",
                        in_path,
                        "--merge",
                        "--dir",
                        "-t", ".1",
                        "--acodec", "pcm_s16le"])

    out_temp = os.path.join(in_dir, "normalized")
    logger.debug(f"Moving files from \"{out_temp}\" into \"{out_dir}\"...")
    for file in os.listdir(out_temp):
        destination_path = os.path.join(out_dir, file)
        shutil.move(os.path.join(out_temp, file), destination_path)
    shutil.rmtree(out_temp)

    logger.info("Finished normalizing volume levels")


def augment_dirty_dir(clean_dir, dirty_dir, out_dir):
    """Augment the dirty examples by mixing clean speech with noise
    If the files being merged have a different length, the duration of the shortest
    file will be used and the other one will be cropped.
    """
    num_augment = min(len(os.listdir(clean_dir)), len(os.listdir(dirty_dir)), NUM_AUGMENT)
    # Combine num_augment random clean files and num_augment random dirty files
    logger.info(f"Augmenting dirty files dataset files by {num_augment} files...")
    make_dir(out_dir)
    clean_files = random.sample(os.listdir(clean_dir), num_augment)
    dirty_files = random.sample(os.listdir(dirty_dir), num_augment)
    for idx, (clean, dirty) in enumerate(zip(clean_files, dirty_files)):
        if is_audio_file(clean) and is_audio_file(dirty):
            clean_path = os.path.join(clean_dir, clean)
            dirty_path = os.path.join(dirty_dir, dirty)
            merged_name = format_int(idx) + "_" + clean[:5] + dirty[:5] + "_aug.wav"
            merged_path = os.path.join(out_dir, merged_name)

            logger.debug(f"Merging files \"{clean}\" and \"{dirty}\" into \"{merged_name}\"...")
            subprocess.run(["ffmpeg",
                            "-loglevel", "panic",  # Make ffmpeg shut up
                            "-i", clean_path,
                            "-i", dirty_path,
                            "-filter_complex", "amerge",
                            "-threads", str(THREADS),
                            "-ac", "1",  # Output a mono channel
                            merged_path])
        else:
            logger.warn(f"Both \"{clean}\" and \"{dirty}\" should be audiofiles. Skipping them...")

    logger.info(f"Finished augmenting dirty files")


def read_wav_as_np(filename):
    data = wav.read(filename)
    np_arr = data[1].astype("float32") / 32767.0  # Normalize 16-bit format into a [-1, 1] range
    # np_arr = np.array(np_arr)
    return np_arr, data[0]


def convert_np_audio_to_sample_blocks(song_np, block_size):
    block_lists = []
    total_samples = song_np.shape[0]
    num_samples_so_far = 0
    while(num_samples_so_far < total_samples):
        block = song_np[num_samples_so_far:num_samples_so_far+block_size]
        if(block.shape[0] < block_size):
            padding = np.zeros((block_size - block.shape[0],))
            block = np.concatenate((block, padding))
        block_lists.append(block)
        num_samples_so_far += block_size
    return block_lists


def load_training_example(filename, block_size=2048):
    data, bitrate = read_wav_as_np(filename)
    X = convert_np_audio_to_sample_blocks(data, block_size)
    Y = X[1:]
    Y.append(np.zeros(block_size))  # Add special end block composed of all zeros
    return X, Y


def make_dataset_blob(clean_files, dirty_files):

    for file in clean_files:
        pass


def pre_process(clean_dir, dirty_dir, out_dir):
    # Combine a subset of clean and dirty files to create more dirty examples
    logger.info(f"Pre-processing dataset files...")
    set_prefix_size(clean_dir, dirty_dir)  # Files start with 001, 002, etc to avoid duplicate names
    augmented_dir = os.path.join(dirty_dir, "augmented")
    augment_dirty_dir(clean_dir, dirty_dir, augmented_dir)

    # Merge stereo channels, convert audiofiles to wav and set the sampling rate to 41000
    temp_clean_mono = os.path.join(out_dir, "clean_mono")
    temp_dirty_mono = os.path.join(out_dir, "dirty_mono")

    merge_channels(clean_dir, temp_clean_mono)
    merge_channels(dirty_dir, temp_dirty_mono)
    merge_channels(augmented_dir, temp_dirty_mono)

    # Normalize the volume levels
    processed_clean = os.path.join(out_dir, "clean_processed")
    processed_dirty = os.path.join(out_dir, "dirty_processed")

    normalize_volume(temp_clean_mono, processed_clean)
    normalize_volume(temp_dirty_mono, processed_dirty)
    shutil.rmtree(temp_clean_mono)
    shutil.rmtree(temp_dirty_mono)

    # make_dataset_blob(processed_clean, processed_dirty)

    # TODO: Make big binary file of allprocessing files
    logger.info(f"Finished pre-processing dataset files")
