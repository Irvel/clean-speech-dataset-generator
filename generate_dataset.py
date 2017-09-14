from multiprocessing import Pool
import os

import download_internetarchive
import download_librivox
import logging_setup

logger = logging_setup.setup_logger("Dataset Generator")

CLEAN_DIRTY_SPLIT = .5  # What % of our data will be clean speech speech
NUM_PROCESSES = 7
NUM_LANGUAGES = 20
CHAPTERS_PER_LANGUAGE = 4


def download_clean_speech_files(download_dir):
    logger.info(f"Downloading clean speech files to {download_dir}")
    if not os.path.exists(download_dir):
        os.mkdir(download_dir)

    books = download_librivox.fetch_all_books(start_page=1, end_page=90)
    for book in books:
        book.download_dir = download_dir
    download_librivox.fetch_all_books_chapters(books)
    readers = set()
    languages = {}
    for book in books:
        for chapter in book.chapters:
            if chapter.language_code in languages:
                languages[chapter.language_code].append(chapter)
            else:
                languages[chapter.language_code] = [chapter]

    chapters_to_download = []
    # Get at most NUM_LANGUAGES chapter recordings from different speakers
    chaps_per_lang = 0
    for idx, language in enumerate(languages.keys()):
        if idx >= NUM_LANGUAGES:
            break

        for chapter in languages[language]:
            if chaps_per_lang >= CHAPTERS_PER_LANGUAGE:
                break

            # Don't get multiple files from the same reader
            if chapter.reader_name not in readers:
                chaps_per_lang += 1
                readers.add(chapter.reader_name)
                chapters_to_download.append(chapter)

    with Pool(NUM_PROCESSES) as pool:
        pool.map(download_librivox.download_chapter, chapters_to_download)


def download_noise_files(download_dir):
    logger.info(f"Downloading noise files to {download_dir}")
    if not os.path.exists(download_dir):
        os.mkdir(download_dir)

    download_internetarchive.download_n_files(download_dir, 500)


if __name__ == '__main__':
    clean_download_dir = "/Volumes/yes/clean_speech_dataset/clean_files/"
    dirty_download_dir = "/Volumes/yes/clean_speech_dataset/dirty_files/"
    download_clean_speech_files(clean_download_dir)
    download_noise_files(dirty_download_dir)

    # Process downloaded files
