"""
Download Module
- Fetches audio files from Internetarchive
- Attempts to get multiple languages from Librivox archive
- Filters out files that contain hints to "noisy" in the reviews

"""
from internetarchive import search_items
from internetarchive import get_item

NUM_FILES = 10
NUM_PROCESSES = 4
CLEAN_DIRTY_SPLIT = .5  # What % of our data will be clean speech speech
CLEAN_SUBJECTS = ["librivox"]  # TODO: Find out how to actually get the librivox catalog
DIRTY_SUBJECTS = ["music", "instrumental", "78rpm", "ambient", "noise",
                  "drone"]


def is_valid_item(item_metadata):
    # We want audio files


def search_tems(search_query, num_files=NUM_FILES):
    valid_items = []
    more_items_left = True
    search_results = search_items(query=search_query)

    if not search_results:
        raise Exception

    while more_items_left and len(valid_items) < num_files:
        for result in search_results:
            item = get_item(result["identifier"])
            if is_valid_item(item.item_metadata):
                valid_items.append(item)

    return valid_items


def fetch_files(query, destination_dir):
    pass


def make_dataset():
    pass
