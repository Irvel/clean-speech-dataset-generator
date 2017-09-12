from pathlib import Path
from typing import List

import datetime
import os
import random
import shutil

import download_session


LANGUAGE_TO_CODE = {"english": "en", "spanish": "es", "brazilian portuguese": "pt", "portuguese": "pt",
                    "chinese": "zh", "dutch": "nl", "esperanto": "eo", "filipino": "tg", "german": "de",
                    "japanese": "jp", "malay": "ms", "polish": "pl", "acehnese": "ace", "balinese": "ban",
                    "buginese": "bug", "bulgarian": "bg", "czech": "cs", "faroese": "fo", "western frisian": "fy",
                    "greek": "el", "hebrew": "he", "indonesian": "id", "javanese": "jv", "latvian": "lt",
                    "luxembourgish": "lb", "minangkabau": "min", "nynorsk": "nn", "occitan": "oc",
                    "occitan (languedocien)": "oc", "occitan languedocien": "oc", "languedocien": "oc", "oriya": "or",
                    "pampango": "pam", "slovak": "sk", "swedish": "sv", "ancient greek": "el",
                    "cantonese chinese": "zh", "albanian": "sq", "aragonese": "an", "armenian": "hy", "igbo": "ig",
                    "icelandic": "is", "ido": "io", "nuosu": "ii", "sichuan yi": "ii", "arabic": "ar",
                    "cebuano": "ceb", "bisaya": "ceb", "church slavonic": "cu", "slavonic": "cu",
                    "old bulgarian": "cu", "church slavic": "cu", "old slavonic": "cu", "old church slavonic": "cu",
                    "chuvash": "cv", "cornish": "kw", "croatian": "hr", "luo": "luo", "dholuo": "luo",
                    "galician": "gl", "irish": "ga", "tagalog": "tl", "wikang tagalog": "tl", "yiddish": "yi"}

CODE_TO_LANGUAGE = {language: code for code, language in LANGUAGE_TO_CODE.items()}


class Chapter:
    """Stores a LibriVox Book Chapter's metadata."""
    title: str = None
    number: int = None
    author: str = None
    _language_code: str = None
    _duration: datetime.timedelta = None
    size: str = None
    reader_name: str = None
    book = None
    _download_url: str = None
    _download_path: str = None
    _download_dir: str = None
    _download_filename: str = None

    def __init__(self, book_reference):
        self.book = book_reference

    @property
    def download_url(self):
        return self._download_url

    @download_url.setter
    def download_url(self, new_url):
        """Updates the URL and filename of the Chapter."""
        self._download_url = new_url

        if not self.download_filename:
            self.download_filename = new_url.split("/")[-1]

    @property
    def download_dir(self):
        return self._download_dir

    @download_dir.setter
    def download_dir(self, new_dir):
        """Updates the download dir and path of the chapter in storage."""
        new_dir = new_dir.strip()
        self._ensure_dir_exists(new_dir)

        if self._download_path and self.is_downloaded:
            self._move_self_to(new_dir=new_dir)

        self._download_dir = new_dir
        self._update_full_path()

    @property
    def download_filename(self):
        return self._download_filename

    @download_filename.setter
    def download_filename(self, new_name):
        """Updates the download filename and path of the chapter in storage."""
        new_name = new_name.strip()

        if self._download_path and self.is_downloaded:
            self._move_self_to(new_name=new_name)

        self._download_filename = new_name
        self._update_full_path()

    @property
    def download_path(self):
        return self._download_path

    @property
    def duration(self):
        return self._duration

    @duration.setter
    def duration(self, text_duration: str):
        """Takes a string 00:00:00 and stores it as a timedelta object."""
        self._duration = text_to_timedelta(text_duration)

    @duration.setter
    def duration(self, timedelta_duration: datetime.timedelta):
        self._duration = timedelta_duration

    @property
    def is_downloaded(self):
        """Return if the chapter has been downloaded."""
        if not self.download_path:
            return False
        return Path(self.download_path).exists()

    @property
    def language_code(self):
        return self._language_code

    @language_code.setter
    def language_code(self, new_code):
        self._language_code = new_code

    @property
    def language(self):
        if self.language_code in CODE_TO_LANGUAGE:
            return CODE_TO_LANGUAGE[self.language_code]

        return self.language_code

    @language.setter
    def language(self, text_language):
        """Convert a language name into it's language code."""
        language = text_language.strip().lower()
        if language in LANGUAGE_TO_CODE:
            self._language_code = LANGUAGE_TO_CODE[language]
        else:
            self._language_code = language[:2]

    def download(self, overwrite=False):
        """Download the chapter from a URL to storage.

        Args:
            overwrite: Whether to overwrite a previously downloaded file.

        Returns:
            True if successful, False otherwise.

        Raises:
            Exception: No valid download directory or URL was set

        """
        if not self.download_dir:
            raise Exception("A target download directory was not has not been set.")

        if not self.download_url:
            raise Exception("A download URL has not been set.")

        if not self.is_downloaded or overwrite:
            session = download_session.make_session()
            try:
                download_request = session.get(self.download_url, stream=True, timeout=10)
                if download_request.stats_code != 200:
                    with open(self.download_path, "wb") as local_file:
                        # TODO: Replace this with proper logging
                        print(f"Downloading {self.download_filename} to {self.download_dir} ...")
                        shutil.copyfileobj(download_request.raw, local_file)

            except download_session.get_download_exceptions() as e:
                print(e)

            else:
                if Path(self.download_path).exists():
                    return True
        else:
            print("File exists, skipping re-downloading...")
            return True

        return False

    def _ensure_dir_exists(self, directory):
        """Create a directory for the target download."""
        directory = directory.strip()
        if not Path(self.download_path).exists():
            os.mkdir(directory)

    def _move_self_to(self, new_dir=None, new_name=None):
        if self.is_downloaded:
            if new_dir and not new_name:
                shutil.move(self._download_path, os.path.join(new_dir, self.download_filename))
            elif new_name and not new_dir:
                shutil.move(self._download_path, os.path.join(self.download_dir, new_name))
            elif new_name and new_dir:
                shutil.move(self._download_path, os.path.join(new_dir, new_name))

    def _update_full_path(self):
        if self.download_dir and self.download_filename:
            self._download_path = os.path.join(self.download_dir,
                                               self.download_filename)
        else:
            self._download_path = None

    def __repr__(self):
        return (f"Download URL:{self.download_url}     \nTitle:{self.title}    Number:{self.number}    " +
                f"Language Code:{self.language_code}    Duration:{self._duration}    " +
                f"Size:{self.size}    Reader:{self.reader_name}    Book:{self.book.title}     " +
                f"Download Path:{self._download_path}\n")


class Book:
    """Stores a LibriVox Book's metadata."""
    title: str = None
    author: str = None
    url: str = None
    _language_code: str = None
    _duration: int = None
    zip_download_url: str = None
    date: str = None
    size: str = None
    proof_listener: str = None
    proof_listener_url: str = None
    chapters: List[Chapter] = None

    @property
    def duration(self):
        return self._duration

    @duration.setter
    def duration(self, text_duration: str):
        """Takes a string 00:00:00 and stores it as a timedelta object."""
        self._duration = text_to_timedelta(text_duration)

    @duration.setter
    def duration(self, timedelta_duration: datetime.timedelta):
        self._duration = timedelta_duration

    @property
    def language_code(self):
        return self._language_code

    @property
    def language(self):
        if self.language_code in CODE_TO_LANGUAGE:
            return CODE_TO_LANGUAGE[self.language_code]

        return self.language_code

    @language.setter
    def language(self, text_language):
        """Convert a language name into it's language code."""
        language = text_language.strip().lower()
        if language in LANGUAGE_TO_CODE:
            self._language_code = LANGUAGE_TO_CODE[language]
        else:
            self._language_code = language[:2]

    def get_random_chapters(self, amount=1):
        if self.chapters:
            return random.sample(self.chapters, amount)
        return []

    # FIXME: Printing a list of books does not print this
    def __repr__(self):
        return (f"\n\nBook title: {self.title}\nBook author: {self.author}\nBook URL: {self.url}\n" +
                f"Book ZIP Download URL: {self.zip_download_url}\nBook size: {self.size}\n" +
                f"Book chapter count: {len(self.chapters)}\n\n" +
                f"======================== Book Chapters ========================\n{self.chapters}\n\n\n")


def text_to_timedelta(text):
    """Parses a 00:00:00 string a into a timedelta object"""
    parts = text.strip().split(":")
    if len(parts) == 3:
        hours = parts[0].strip()
        minutes = parts[1].strip()
        seconds = parts[2].strip()
        if hours.isnumeric and minutes.isnumeric and seconds.isnumeric:
            hours = int(hours)
            minutes = int(minutes)
            seconds = int(seconds)
            return datetime.timedelta(hours=hours, minutes=minutes, seconds=seconds)

    return datetime.timedelta()
