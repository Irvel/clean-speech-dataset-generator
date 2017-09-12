"""
A simple librivox scraper

Fetches every available title
"""
from bs4 import BeautifulSoup
from multiprocessing import Pool

import json
import requests
import random

from book import Book
from book import Chapter
import download_session


NUM_PROCESSES = 5  # Number of processes to use for downloading
MAX_KNOWN_PAGE = 445  # The last know page from the book catalog

MAGIC_HEADERS = {"Referer": "https://librivox.org/search",
                 "Host": "librivox.org",
                 "Accept": "*/*",
                 "Connection": "keep-alive",
                 "Accept-Language": "en-us",
                 "Accept-Encoding": "br, gzip, deflate",
                 "User-Agent": "",
                 "X-Requested-With": "XMLHttpRequest"}

USER_AGENTS = ["Mozilla/5.0 (Macintosh; Intel Mac OS X 10.7; rv:11.0) Gecko/20100101 Firefox/11.0",
               "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:22.0) Gecko/20100 101 Firefox/22.0",
               "Mozilla/5.0 (Windows NT 6.1; rv:11.0) Gecko/20100101 Firefox/11.0",
               ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_4) AppleWebKit/536.5 (KHTML, like Gecko) "
                "Chrome/19.0.1084.46 Safari/536.5"),
               ("Mozilla/5.0 (Windows; Windows NT 6.1) AppleWebKit/536.5 (KHTML, like Gecko) Chrome/19.0.1084.46"
                "Safari/536.5"),
               ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13) AppleWebKit/604.1.38 (KHTML, like Gecko) "
                "Version/11.0 Safari/604.1.38")]

# Used to get the list of languages
LANGUAGES_URL = "https://librivox.org/search/get_results?primary_key=0&search_category=language&sub_category=&search_page=1&search_order=alpha&project_type=either"

# Fetch every title
TITLES_URL = "https://librivox.org/search/get_results?primary_key=0&search_category=title&search_order=alpha&project_type=either"


# Get a list languages an the amount of Audiobooks in each language
def get_languages():
    pass


def fetch_titles_from_page(page_number, get_books=True):
    """Fetch book details from a specific catalog page.

    Instead downloading the entire book as .zip, we want to download many individual chapters from different books
    to add more variety to our training set.

    Args:
        page_number (int): The page number book catalog to fetch.
        get_books (str): Whether to actually scrape the books info from the catalog.

    Returns:
        True if successful, False otherwise.

    """
    print(f"Downloading page {page_number}... ", end="")
    url = TITLES_URL + f"&search_page={page_number}"
    result = requests.get(url, headers=MAGIC_HEADERS)

    if result.status_code != 200:
        return [], False

    json_result = json.loads(result.text)
    if json_result["status"] != "SUCCESS":
        return [], False

    if json_result["results"] == "No results":
        return [], False

    books = []
    if get_books:
        html_results = json_result["results"]
        scraper = BeautifulSoup(html_results, 'html.parser')
        catalog_results = scraper.find_all("li", class_="catalog-result")

        for catalog_result in catalog_results:
            book = Book()
            result_data = catalog_result.find_next("div", class_="result-data")
            book.title = result_data.a.text
            book.url = result_data.a.attrs["href"]
            book.author = result_data.find_all(class_="book-author")[0].a.text
            book.zip_download_url = catalog_result.find_next(class_="download-btn").a.attrs["href"]
            book.size = catalog_result.find_next(class_="download-btn").span.text.strip()
            books.append(book)

        print(f"{True}, Fetched metadata for {len(books)} books.")

    print()
    return books, True


def fetch_all_books(max_page=MAX_KNOWN_PAGE, need_update_page=True):
    """Fetches metadata for all books from the titles catalog."""

    while need_update_page:
        _, need_update_page = fetch_titles_from_page(max_page, False)
        if need_update_page:
            max_page += 1

    fetched_titles = []
    with Pool(NUM_PROCESSES) as pool:
        fetched_titles = pool.map(fetch_titles_from_page, [n for n in range(max_page)])

    all_books = []
    for result in fetched_titles:
        if result[1]:
            all_books.extend(result[0])

    return all_books


def fetch_all_chapters(book):
    # FIXME: This function turned out to be way too large, try to split it
    print(f"Downloading chapters for book: {book.title}   at   {book.url}")
    session = download_session.make_session()
    book_page = session.get(book.url, headers=MAGIC_HEADERS, timeout=10)
    if book_page.status_code != 200:
        # TODO: Replace this with proper colored nice logging
        print("\n\n\n\n\n\n")
        print("COULD NOT MAKE REQUEST")
        print("\n\n\n\n\n\n")
        return []

    # Get missing book metadata
    scraper = BeautifulSoup(book_page.text, 'html.parser')
    juicy_info = scraper.find("dl", class_="product-details clearfix").find_all("dd")
    book.duration = juicy_info[0].text
    # If the book size was not set before for some reason
    if not book.size:
        book.size = juicy_info[1].text.strip()
    book.date = juicy_info[2].text
    if juicy_info[6].a and juicy_info[6].a.text.replace("\xa0", "").strip():
        book.proof_listener = juicy_info[6].a.text.replace("\xa0", "").strip()
        book.proof_listener_url = juicy_info[6].a.attrs["href"]

    book.description = scraper.find("div", class_="page book-page").find("div", class_="description").text
    lang_group_gen = scraper.find_all("p", class_="book-page-genre")

    if lang_group_gen:
        book.genre = lang_group_gen[0].text.replace("Genre(s):", "").strip()
        if len(lang_group_gen) > 1:
            book.language = lang_group_gen[1].text.replace("Language:", "").strip()
            if len(lang_group_gen) > 2:
                book.group = lang_group_gen[2].text.replace("Group:", "").strip()
    else:
        # TODO: Replace this with proper colored nice logging
        print("\n\n\n\n\n\n")
        print("COULDNT FIND lang_group_gen")
        print(lang_group_gen)
        print("\n\n\n\n\n\n")

    # Get the chapters information
    chapters = []
    chapters_table = scraper.find("table", class_="chapter-download")
    if not chapters_table:
        # TODO: Replace this with proper colored nice logging
        print("\n\n\n\n\n\n")
        print("COULDNT FIND table class_=chapter-download")
        print(scraper)
        print("\n\n\n\n\n\n")
        return chapters

    chapter_rows = chapters_table.find_all("tr")[1:]  # The first row is the table headers
    if not chapter_rows:
        # TODO: Replace this with proper colored nice logging
        print("\n\n\n\n\n\n")
        print("COULDNT FIND tr[1:] IN chapters_table")
        print(chapters_table)
        print("\n\n\n\n\n\n")
        return chapters

    if len(chapter_rows[0].find_all("td")) == 7:
        for row in chapter_rows:
            chapter = Chapter(book)
            chapter.title = row.find("a", class_="chapter-name").text
            chapter.download_url = row.find("a", class_="chapter-name").attrs["href"]
            row_elements = row.find_all("td")
            chapter.number = int(row_elements[0].text.replace(row_elements[0].a.text, "").strip())
            chapter.author = row_elements[2].text.strip()
            if row_elements[2].a:
                chapter.author_url = row_elements[2].a.attrs["href"]

            chapter.source_text = row_elements[3].text.strip()
            if row_elements[3].a:
                chapter.source_text_url = row_elements[3].a.attrs["href"]

            chapter.reader_name = row_elements[4].text.strip()
            if row_elements[4].a:
                chapter.reader_url = row_elements[4].a.attrs["href"]

            chapter.duration = row_elements[5].text.strip()
            chapter.language_code = row_elements[6].text.strip()
            chapters.append(chapter)

    elif len(chapter_rows[0].find_all("td")) == 4:
        for row in chapter_rows:
            chapter = Chapter(book)
            chapter.title = row.find("a", class_="chapter-name").text
            chapter.download_url = row.find("a", class_="chapter-name").attrs["href"]
            row_elements = row.find_all("td")
            chapter.number = int(row_elements[0].text.replace(row_elements[0].a.text, "").strip())

            chapter.reader_name = row_elements[2].text.strip()
            # Chapters read by a group of people don't have a link to the reader's profile
            if row_elements[2].a:
                chapter.reader_url = row_elements[2].a.attrs["href"]

            chapter.duration = row_elements[3].text.strip()
            chapter.language = book.language
            chapter.author = book.author
            chapters.append(chapter)
    else:
        # TODO: Replace this with proper colored nice logging
        print("\n\n\n\n\n\n")
        print("BAD LENGTH: len: ", end=" ")
        print(len(chapter_rows[0]))
        print(chapter_rows)
        print("\n\n\n\n\n\n")

    return chapters


def fetch_all_books_chapters(books):
    """Fetches metadata for all chapters in the received books."""
    with Pool(NUM_PROCESSES) as pool:
        lists_of_chapters = pool.map(fetch_all_chapters, books)

    for book, chapters in zip(books, lists_of_chapters):
        book.chapters = chapters


if __name__ == '__main__':
    books = fetch_all_books(2, False)
    fetch_all_books_chapters(books)
    print(books[0])
    #[print(b) for b in books]

