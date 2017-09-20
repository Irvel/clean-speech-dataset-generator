"""Generate a Clean Speech/Noise dataset"""
from multiprocessing import Pool
import os

import download_internetarchive
import download_librivox
import logging_setup
import pre_process_files

logger = logging_setup.setup_logger("Dataset Generator")

CLEAN_DIRTY_SPLIT = .5  # What % of our data will be clean speech speech
NUM_PROCESSES = 1
NUM_LANGUAGES = 30
CHAPTERS_PER_LANGUAGE = 15


def download_clean_speech_files(download_dir):
    logger.info(f"Downloading clean speech files to {download_dir}")
    if not os.path.exists(download_dir):
        os.mkdir(download_dir)

    books = download_librivox.fetch_all_books(start_page=200, end_page=400)
    logger.info(f"Downloaded information for {len(books)} books from LibriVox")
    for book in books:
        book.download_dir = download_dir
    download_librivox.fetch_all_books_chapters(books)
    readers = set()
    languages = {}
    chapter_count = 0
    for book in books:
        for chapter in book.chapters:
            if chapter.language_code in languages:
                languages[chapter.language_code].append(chapter)
            else:
                languages[chapter.language_code] = [chapter]
            chapter_count += 1

    logger.info(f"Downloaded information for {chapter_count} chapters in {len(languages.keys())} languages")
    chapters_to_download = []
    # Get at most NUM_LANGUAGES chapter recordings from different speakers
    for idx, language in enumerate(languages.keys()):
        if idx >= NUM_LANGUAGES:
            break
        chaps_per_lang = 0
        for chapter in languages[language]:
            if chaps_per_lang >= CHAPTERS_PER_LANGUAGE:
                break

            # Don't get multiple files from the same reader
            if chapter.reader_name not in readers:
                chaps_per_lang += 1
                readers.add(chapter.reader_name)
                chapters_to_download.append(chapter)

    """
    # Commenting out multiprocess code for now as it crashes in Python 3.6.2 with the error:
    # "__NSPlaceholderDate initialize] may have been in progress in another thread when fork() was called."
    with Pool(NUM_PROCESSES) as pool:
        pool.map(download_librivox.download_chapter, chapters_to_download)
    """
    for chapter in chapters_to_download:
        chapter.download()


def download_noise_files(download_dir):
    logger.info(f"Downloading noise files to {download_dir}")
    if not os.path.exists(download_dir):
        os.mkdir(download_dir)

    download_internetarchive.download_n_files(download_dir, 300)


if __name__ == '__main__':
    clean_download_dir = "/Volumes/yes/clean_speech_dataset_2/clean_files/"
    dirty_download_dir = "/Volumes/yes/clean_speech_dataset_2/dirty_files/"
    # TODO: Only download clean speech files with good quality
    #download_clean_speech_files(clean_download_dir)
    download_noise_files(dirty_download_dir)
    pre_process_files.pre_process(clean_download_dir, dirty_download_dir, "/Volumes/yes/clean_speech_dataset_2")

    # Process downloaded files
