"""
Downloads internetarchive.org audio files from a set of pre-defined categories.

Uses the internetarchive Python package to download audio items from a specific
set of categories (DIRTY_CATEGORIES). These categories are considered "dirty"
because they are not "clean speech" (undistorted human speech without background
noise).
"""
import internetarchive
import math
import os

import logging_setup

logger = logging_setup.setup_logger("InternetArchive Module")

NUM_FILES = 10
NUM_PROCESSES = 8
DIRTY_CATEGORIES = ["music", "instrumental", "78rpm", "ambient", "noise", "drone"]
"""These weights determine how many files of each category we're going to get.
They are based on empirically determined "importance" of each category.
Categories of sounds that have a low shannon entropy value have a smaller weight.
For example, the "drone" category consists of sounds that are characterized by a
repetitive "humm". These type of sounds do not contain a lot of information and thus
we don't want to download a lot of files in these category.
"""
CATEGORIES_WEIGHTS = [0.117, 0.315, 0.076, 0.38, 0.085, 0.03]
VALID_EXTENSIONS = [".mp3", ".mp4", ".ogg", ".wav", ".aac", ".m4b"]


def is_valid_item(item_metadata):
    # We want audio files
    pass


def fetch_items_in_query(search_query, num_items):
    items = []
    for item in internetarchive.search_items(query=search_query):
        if len(items) < num_items:
            item_id = item["identifier"]
            item = internetarchive.get_item(item_id)
            if item:
                logger.info(f"Fetched item \"{item_id}\"")
                items.append(item)
        else:
            break
    return items


def make_category_query(category):
    """Creates a search query for the target audio category"""
    # mediatype:(audio) subject:"radio"
    return f"mediatype:(audio) subject:{category}"


def fetch_total_n_items(num_items, uniform_distribution=False):
    """Get num_items files from internet archive in our dirty categories list"""
    logger.info(f"Fetching info for {num_items} internetarchive items...")
    categories_weights = CATEGORIES_WEIGHTS
    if uniform_distribution:
        categories_weights = [1/len(DIRTY_CATEGORIES) for x in range(len(DIRTY_CATEGORIES))]

    how_many_of_each_cat = [math.ceil(w * num_items) for w in categories_weights]

    total_items = []
    for amount, category in zip(how_many_of_each_cat, DIRTY_CATEGORIES):
        query = make_category_query(category)
        total_items.extend(fetch_items_in_query(query, amount))

    return total_items


def download_n_files(destination_dir, num_files=NUM_FILES):
    items = fetch_total_n_items(num_files)
    total_downloaded_size = 0
    # If there are multiple formats available for the same file, only download one
    for item in items:
        file_name = None
        file_size = None
        for file in item.files:
            for extension in VALID_EXTENSIONS:
                if extension in file["name"]:
                    # We only want to download one file per item so if there are multiple files
                    # with a valid extension in an item, we'll only download the first file.
                    file_name = file["name"]
                    file_size = file["size"]
                    break
            if file_name:
                break

        if file_name:
            try:
                logger.info(f"Trying to download \"{file_name}\" from internetarchive...")
                item.download(glob_pattern=file_name, no_directory=True, ignore_existing=True,
                              destdir=destination_dir, retries=10, silent=True)
                total_downloaded_size += int(file_size)
            except Exception as e:
                logger.error(f"Failed to download file \"{file_name}\" internetarchive")
                logger.error(e)
                total_downloaded_size -= file_size
                os.remove(os.path.join(destination_dir, file_name))

    return total_downloaded_size


if __name__ == '__main__':
    downloaded_bytes = 0
    while downloaded_bytes < 10000:
        downloaded_bytes += download_n_files("/Users/irvel/Desktop/download_a_lot/", 10)
