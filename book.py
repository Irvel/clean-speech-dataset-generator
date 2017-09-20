from pathlib import Path
from typing import List

import datetime
import os
import random
import shutil

import download_session
import logging_setup

logger = logging_setup.setup_logger("Book Module")


LANGUAGE_TO_CODE = {"english": "en", "spanish": "es", "brazilian portuguese": "pt", "portuguese": "pt",
                    "chinese": "zh", "dutch": "nl", "esperanto": "eo", "filipino": "tg", "german": "de",
                    "japanese": "jp", "malay": "ms", "polish": "pl", "acehnese": "ace", "balinese": "ban",
                    "buginese": "bug", "bulgarian": "bg", "czech": "cs", "faroese": "fo", "western frisian": "fy",
                    "greek": "el", "hebrew": "he", "indonesian": "id", "javanese": "jv", "latvian": "lv",
                    "latvian (latvia)": "lv", "luxembourgish": "lb", "minangkabau": "min", "nynorsk": "nn",
                    "occitan": "oc", "occitan (languedocien)": "oc", "occitan languedocien": "oc", "languedocien": "oc",
                    "oriya": "or", "pampango": "pam", "slovak": "sk", "swedish": "sv", "ancient greek": "el",
                    "cantonese chinese": "zh", "albanian": "sq", "aragonese": "an", "armenian": "hy", "igbo": "ig",
                    "icelandic": "is", "ido": "io", "nuosu": "ii", "sichuan yi": "ii", "arabic": "ar",
                    "cebuano": "ceb", "bisaya": "ceb", "church slavonic": "cu", "slavonic": "cu",
                    "old bulgarian": "cu", "church slavic": "cu", "old slavonic": "cu", "old church slavonic": "cu",
                    "chuvash": "cv", "cornish": "kw", "croatian": "hr", "luo": "luo", "dholuo": "luo",
                    "galician": "gl", "irish": "ga", "tagalog": "tl", "wikang tagalog": "tl", "yiddish": "yi",
                    "multilingual": "multi", "maori": "mi", "danish": "da", "romanian": "ro"}

CODE_TO_LANGUAGE = {language: code for code, language in LANGUAGE_TO_CODE.items()}


class AudioBookFile:
    title: str = None
    author: str = None
    _language_code: str = None
    _download_url: str = None
    _download_dir: str = None
    _download_filename: str = None
    _download_path: str = None
    _duration: datetime.timedelta = None
    _size: int = None  # Filesize in bytes

    @property
    def language_code(self) -> str:
        return self._language_code

    @language_code.setter
    def language_code(self, new_code):
        self._language_code = new_code

    @property
    def language(self) -> str:
        """The language name in which the AudioFile is recorded in."""
        if self.language_code in CODE_TO_LANGUAGE:
            return CODE_TO_LANGUAGE[self.language_code]

        return self.language_code

    @language.setter
    def language(self, text_language):
        """Set the language code via a language name."""
        language = text_language.strip().lower()
        if language in LANGUAGE_TO_CODE:
            self._language_code = LANGUAGE_TO_CODE[language]
        else:
            self._language_code = language[:2]

    @property
    def download_url(self) -> str:
        """The direct url to download the AudioFile."""
        return self._download_url

    @download_url.setter
    def download_url(self, new_url):
        """Updates the URL and filename of the AudioBookFile."""
        self._download_url = new_url

        if not self.download_filename:
            lang_code = ""
            if self.language_code:
                lang_code = self.language_code
            self.download_filename = lang_code + "_" + new_url.split("/")[-1]

    @property
    def download_dir(self) -> str:
        """The download directory to which the AudioFile will download itself in."""
        return self._download_dir

    @download_dir.setter
    def download_dir(self, new_dir):
        """Updates the download dir and path of the AudioBookFile in storage."""
        new_dir = new_dir.strip()
        self._ensure_dir_exists(new_dir)

        if self._download_path and self.is_downloaded:
            self._move_self_to(new_dir=new_dir)

        self._download_dir = new_dir
        self._update_full_path()

    @property
    def download_filename(self) -> str:
        """The filename of the AudioFile that it will download itself to.

        If the filename is not explicitly set, the filename of the file on the server reachable
        via the self.download_url is used.
        """
        return self._download_filename

    @download_filename.setter
    def download_filename(self, new_name):
        """Updates the download filename and path of the AudioBookFile in storage."""
        new_name = new_name.strip()

        if self._download_path and self.is_downloaded:
            self._move_self_to(new_name=new_name)

        self._download_filename = new_name
        self._update_full_path()

    @property
    def download_path(self) -> str:
        """Full download path that reflects the combination of download_dir and download_filename."""
        return self._download_path

    @property
    def duration(self) -> datetime.timedelta:
        """The duration of the AudioFile recording in a timedelta object."""
        return self._duration

    @duration.setter
    def duration(self, duration):
        """Takes duration either string 00:00:00 or a timedelta object."""
        if type(duration) is str:
            self._duration = self._text_to_timedelta(duration)
        elif type(duration) is datetime.timedelta:
            self._duration = duration
        else:
            raise Exception("Wrong duration type provided")

    @property
    def size(self) -> int:
        """The filesize in bytes of the AudioFile."""
        return self._size

    @property
    def size_str(self) -> str:
        """Get a human readable representation of the size in bytes."""
        return fmt_size_bytes(self._size)

    @size.setter
    def size(self, new_size):
        """Takes filesize in either text with units or bytes in an integer."""
        if type(new_size) is str:
            new_size = new_size.replace(" ", "").upper()
            new_size = new_size.replace(")", "")
            new_size = new_size.replace("(", "")
            new_size = new_size.replace(",", ".")
            new_size = new_size.replace("B", "").strip()
            target_unit = None
            multiplier = 1
            is_bytes = False
            try:
                float(new_size)
                target_unit = "B"
                is_bytes = True
            except Exception as e:
                pass

            if not is_bytes:
                multiplier *= 1024
                for unit in ["K", "M", "G", "T", "P", "E", "Z", "Y"]:
                    if not target_unit and unit in new_size:
                        target_unit = unit
                        multiplier *= 1024
                    # Reject double units
                    elif target_unit and unit in new_size:
                        target_unit = None
                        break

            if target_unit:
                new_size = new_size.replace(target_unit, "").strip()
                try:
                    self._size = int(float(new_size) * multiplier)
                except Exception as e:
                    logger.error(f"Failed to set a size from \"{new_size}\"")
                    logger.error(e)

        elif type(new_size) is int:
            self._size = new_size

        else:
            raise Exception("Wrong size type provided ({type(new_size)})")

        if not self._size:
            logger.warn(f"Failed to set a size from \"{new_size}\"")

    @property
    def is_downloaded(self) -> bool:
        """Return if the AudioFile has been downloaded to the current download_path location."""
        if not self.download_path:
            return False
        return Path(self.download_path).exists()

    def _ensure_dir_exists(self, directory):
        """Create a directory for the target download."""
        directory = directory.strip()
        if not Path(directory).exists():
            os.mkdir(directory)

    def _move_self_to(self, new_dir=None, new_name=None):
        """Move the downloaded AudioFile into a location."""
        if self.is_downloaded:
            if new_dir and not new_name:
                shutil.move(self._download_path, os.path.join(new_dir, self.download_filename))
            elif new_name and not new_dir:
                shutil.move(self._download_path, os.path.join(self.download_dir, new_name))
            elif new_name and new_dir:
                shutil.move(self._download_path, os.path.join(new_dir, new_name))

    def _update_full_path(self):
        """Keep a shorthand access to the full dir + filename representation."""
        if self.download_dir and self.download_filename:
            self._download_path = os.path.join(self.download_dir,
                                               self.download_filename)
        else:
            self._download_path = None

    def _text_to_timedelta(self, text: str) -> datetime.timedelta:
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

        return None

    def delete_file(self):
        if self.is_downloaded():
            os.remove(self.download_path)

    def __repr__(self):
        return (f"title: {self.title} author: {self.author} download URL: {self.download_url}  "
                f"size: {self.size} duration:{self._duration} ")


class Chapter(AudioBookFile):
    """Stores a LibriVox Book Chapter's metadata."""
    reader_name: str = None
    book = None

    def __init__(self, book_reference):
        self.book = book_reference
        # Copy our parent book download directory if set
        if book_reference and book_reference.download_dir:
            self.download_dir = book_reference.download_dir

        if book_reference.language_code and not self.language_code:
            self.language_code = book_reference.language_code

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
                download_request = session.get(self.download_url, stream=True, timeout=120)
                if download_request.status_code == 200:
                    # Maybe we should assert 'Content-Type': 'audio/mpeg' here?
                    if not self.size:
                        self.size = int(download_request.headers["Content-Length"])

                    with open(self.download_path, "wb") as local_file:
                        logger.info(f"Downloading {self.download_filename} to \"{self.download_dir}\"...")
                        shutil.copyfileobj(download_request.raw, local_file)

            except Exception as e:
                logger.error(f"Failed to download \"{self.download_filename}\" from \"{self.download_url}\"")
                logger.error(e)
                self.delete_file()

            else:
                if Path(self.download_path).exists():
                    return True
        else:
            logger.info(f"File \"{self.download_filename}\" exists, skipping re-downloading...")
            return True

        return False

    def __repr__(self):
        rep = super(Chapter, self).__repr__()
        return (rep + f"Chap#:{self.number}  language_code:{self.language_code}  "
                f"reader:{self.reader_name} book:{self.book.title}  ")


class Book(AudioBookFile):
    """Stores a LibriVox Book's metadata."""
    author: str = None
    author_url: str = None
    url: str = None
    date: str = None
    proof_listener: str = None
    proof_listener_url: str = None
    chapters: List[Chapter] = None

    def get_random_chapters(self, amount=1) -> [Chapter]:
        if self.chapters:
            return random.sample(self.chapters, amount)
        return []

    def download(self):
        if self.chapters:
            for chapter in self.chapters:
                if chapter:
                    chapter.download()

    def __repr__(self):
        return (f"\n\nBook title: {self.title}\nBook author: {self.author}\nBook URL: {self.url}\n" +
                f"Book download URL: {self.download_url}\nBook size: {self.size}\n" +
                f"Book chapter count: {len(self.chapters)}\n\n" +
                f"======================== Book Chapters ========================\n{self.chapters}\n\n\n")


def fmt_size_bytes(num_bytes: int) -> str:
    num_bytes = float(num_bytes)
    for unit in ["B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB"]:
        if abs(num_bytes) < 1024.0:
            return "%3.1f%s" % (num_bytes, unit)
        num_bytes = num_bytes / 1024.0

    return "%.1f%s" % (num_bytes, "YB")
