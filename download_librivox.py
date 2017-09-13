"""
A simple LibriVox scraper

Fetches information of every available audiobook in LibriVox's repository by scraping librivox.org
with BeautifulSoup. It uses the "Browsing by Title" book catalog in librivox.org as the source for
book metadata. It then stores the information of each book in book.Book objects.
"""
from bs4 import BeautifulSoup
from multiprocessing import Pool


import json
import logging
import random
import requests

from book import Book
from book import Chapter
from book import fmt_size_bytes
import download_session
import logging_setup

logger = logging_setup.setup_logger("LibriVox Scraper")


NUM_PROCESSES = 6  # Number of processes to use for downloading
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

# The "Browsing by Title" book catalog in page librivox.org
TITLES_URL = "https://librivox.org/search/get_results?primary_key=0&search_category=title&search_order=alpha&project_type=either"


def _get_scrape_headers():
    random_ua = random.sample(USER_AGENTS, 1)[0]
    headers = MAGIC_HEADERS
    headers["User-Agent"] = random_ua
    return headers


def fetch_titles_from_page(page_number, get_books=True) -> ([Book], bool):
    """Fetch book details from a specific catalog page.

    Instead downloading the entire book as .zip, we want to download many individual chapters
    from different books to add more variety to our training set.

    In case of not being able to download anything, this function should return an empty list and
    False.

    Args:
        page_number (int): The page number book catalog to fetch
        get_books (bool): Whether to actually scrape the books info from the catalog

    Returns:
        ([Book], bool): A list of books and True if successful

    """
    assert type(page_number) is int
    assert type(get_books) is bool

    logger.debug(f"Fetching catalog page #{page_number}... ")
    url = TITLES_URL + f"&search_page={page_number}"
    result = requests.get(url, headers=_get_scrape_headers())

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

        if catalog_results:
            for catalog_result in catalog_results:
                book = Book()
                result_data = catalog_result.find("div", class_="result-data")
                book.title = result_data.a.text.strip()
                # Remove enclosing " or ' if any
                if book.title[0] is "\"" or book.title[0] is "'":
                    book.title = book.title[1:]

                if book.title[-1] is "\"" or book.title[-1] is "'":
                    book.title = book.title[:-1]

                book.url = result_data.a.attrs["href"]
                book_author = result_data.find(class_="book-author")
                if book_author and book_author.text:
                    book.author = book_author.text.strip()
                else:
                    logger.error(f"Failed to scrape the author for book \"{book.url}\" "
                                 f"in catalog page #{page_number}")
                if book_author and book_author.a and book_author.a.attrs["href"]:
                    book.author_url = book_author.a.attrs["href"]
                else:
                    # Books with various authors don't have an author url so this might be fine
                    logger.warn(f"Failed to scrape the author url for book \"{book.url}\" "
                                 f"in catalog page #{page_number}")
                book.download_url = catalog_result.find(class_="download-btn").a.attrs["href"]
                book.size = catalog_result.find(class_="download-btn").span.text.strip()
                books.append(book)
            logger.debug(f"Fetched metadata for {len(books)} books from page #{page_number}")

        else:
            logger.warn(f"Failed to fetch books from the catalog page #{page_number}")

    else:
        logger.debug(f"Skipping scraping page #{page_number} for book metadata...")

    return books, True


def fetch_all_books(start_page=1, end_page=MAX_KNOWN_PAGE, need_update_page=False) -> [Book]:
    """Fetches metadata for all books from LibriVox's titles catalog.

    Scrapes {TITLES_URL} pages from start_page till end_page to obtain information of the available
    books. It uses a process per page up to {NUM_PROCESSES} processes because the get request to
    each page can takea while to complete.

    Examples:
        - fetch_all_books(start_page=1, end_page=2, need_update_page=False) will download every book
        in pages 1 and 2.

    Args:
        start_page (int): The starting page in LibriVox's titles catalog to fetch (inclusive)
        end_page (int): The ending page in LibriVox's titles catalog to fetch (inclusive)
        need_update_page (bool): Whether to check if there exist more pages after end_page

    Returns:
        [Book]: The books that it was able to scrape from the provided range
    """
    assert type(start_page) is int
    assert type(end_page) is int
    assert start_page < end_page
    assert type(need_update_page) is bool

    while need_update_page:
        logger.debug(f"Checking if the # of LibriVox catalog pages is larger than {end_page}...")
        _, need_update_page = fetch_titles_from_page(end_page, False)
        if need_update_page:
            end_page += 1
            logger.debug(f"Found new catalog page #{end_page}")

    logger.info(f"Fetching LibriVox's book catalog from pages #{start_page} till #{end_page}...")
    fetched_titles = []
    with Pool(NUM_PROCESSES) as pool:
        fetched_titles = pool.map(fetch_titles_from_page, [n for n in range(start_page, end_page)])

    all_books = []
    for result in fetched_titles:
        if result and result[1]:
            all_books.extend(result[0])

    return all_books


def _fetch_missing_book_metadata(book, scraper):
    """Get additional book information not available in the book catalog pages."""
    additional_book_info = scraper.find("dl", class_="product-details clearfix").find_all("dd")
    # We could get the book title like this but it doesn't seem any different from the fetched one
    # in the catalog pages
    # book_title = scraper.find("h1", class_="").text.strip()

    book.duration = additional_book_info[0].text

    # If the book size was not set before for some reason
    if not book.size:
        book.size = additional_book_info[1].text.strip()
    book.date = additional_book_info[2].text
    if additional_book_info[6].a and additional_book_info[6].a.text.replace("\xa0", "").strip():
        book.proof_listener = additional_book_info[6].a.text.replace("\xa0", "").strip()
        book.proof_listener_url = additional_book_info[6].a.attrs["href"]

    book.description = scraper.find("div", class_="page book-page").find("div", class_="description").text
    lang_group_gen = scraper.find_all("p", class_="book-page-genre")

    if lang_group_gen:
        book.genre = lang_group_gen[0].text.replace("Genre(s):", "").strip()
        if len(lang_group_gen) > 1:
            book.language = lang_group_gen[1].text.replace("Language:", "").strip()
            if len(lang_group_gen) > 2:
                book.group = lang_group_gen[2].text.replace("Group:", "").strip()
    else:
        # This info is not really crucial
        logger.error(f"Scraping failed to find the \"genre, language, group\" details section of \"{book.url}\"")


def fetch_all_chapters(book) -> [Chapter]:
    """Fetch metadata for every chapter in the book."""
    logger.debug(f"Downloading info for chapters in book: \"{book.title[:70]}\"...")
    session = download_session.make_session()
    book_page = session.get(book.url, headers=_get_scrape_headers(), timeout=10)
    if book_page.status_code != 200:
        logger.warn(f"Failed to download chapters information for book \"{book.url}\"")
        return []

    scraper = BeautifulSoup(book_page.text, "html.parser")
    _fetch_missing_book_metadata(book, scraper)

    # Get the chapters information
    chapters = []
    chapters_table = scraper.find("table", class_="chapter-download")
    if not chapters_table:
        logger.error(f"Scraping failed to find the chapters table for book \"{book.url}\"")
        return chapters

    chapter_rows = chapters_table.find_all("tr")[1:]  # The first row is the table headers
    if not chapter_rows:
        logger.error(f"Scraping failed to find the chapters rows in the chapters table for book \"{book.url}\"")
        return chapters

    num_row_elements = len(chapter_rows[0].find_all("td"))
    if num_row_elements == 7:
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

    elif num_row_elements == 4:
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
        logger.error(f"Found an unknown number ({num_row_elements}) of chapter_rows in "
                     f"the book page of \"{book.url}\"")

    logger.debug(f"Finished downloading info for {len(chapters)} chapters in book \"{book.title[:50]}\"")
    return chapters


def fetch_all_books_chapters(books):
    """Fetches metadata for all chapters in the received books."""
    with Pool(NUM_PROCESSES) as pool:
        lists_of_chapters = pool.map(fetch_all_chapters, books)

    for booky, chapters in zip(books, lists_of_chapters):
        booky.chapters = chapters


def download_book(target_book):
    target_book.download()


if __name__ == '__main__':
    logger.setLevel(level=logging.DEBUG)
    books = fetch_all_books(start_page=1, end_page=40)
    total_storage = 0
    for booky in books:
        total_storage += booky.size or 0
        booky.download_dir = "/Volumes/yes/clean_speech_files/"
    print(f"\nTOTAL BOOKS SIZE WOULD BE APPROX: {fmt_size_bytes(total_storage)}\n")

    fetch_all_books_chapters(books)

    with Pool(NUM_PROCESSES) as pool:
        _ = pool.map(download_book, books)


    # print(books[0] or "")
    # [print(b) for b in books]
