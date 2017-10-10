# Copyright (C) 2016, 2017 Allen Li
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""DLsite API"""

from pathlib import Path
import re
import shelve
import urllib.request

from bs4 import BeautifulSoup

from mir.dlsite import workinfo


def fetch_work(rjcode: str) -> workinfo.Work:
    """Fetch DLsite work information."""
    page = _get_page(rjcode)
    soup = BeautifulSoup(page, 'lxml')
    work = workinfo.Work(
        rjcode=rjcode,
        name=_get_name(soup),
        maker=_get_maker(soup))
    try:
        series = _get_series(soup)
    except ValueError:
        pass
    else:
        work.series = series
    return work


def _get_page(rjcode: str) -> str:
    """Get webpage text for a work."""
    try:
        request = urllib.request.urlopen(_get_work_url(rjcode))
    except urllib.error.HTTPError as e:
        if e.code != 404:  # pragma: no cover
            raise
        request = urllib.request.urlopen(_get_announce_url(rjcode))
    return request.read().decode()


_ROOT = 'http://www.dlsite.com/maniax/'
_WORK_URL = _ROOT + 'work/=/product_id/{}.html'
_ANNOUNCE_URL = _ROOT + 'announce/=/product_id/{}.html'


def _get_work_url(rjcode: str) -> str:
    """Get DLsite work URL corresponding to an RJ code."""
    return _WORK_URL.format(rjcode)


def _get_announce_url(rjcode: str) -> str:
    """Get DLsite announce URL corresponding to an RJ code."""
    return _ANNOUNCE_URL.format(rjcode)


def _get_name(soup) -> str:
    """Get the work name."""
    return soup.find(id='work_name').a.contents[-1].strip()


def _get_maker(soup) -> str:
    """Get the work maker."""
    return str(
        soup.find(id="work_maker")
        .find(**{'class': 'maker_name'})
        .a.string)


_SERIES_PATTERN = re.compile('^シリーズ名')


def _get_series(soup) -> str:
    """Get work series name."""
    try:
        return str(
            soup.find(id='work_outline')
            .find('th', string=_SERIES_PATTERN)
            .find_next_sibling('td')
            .a.string)
    except AttributeError:
        raise ValueError('no series')


class CachedFetcher:

    def __init__(self, path: 'PathLike', fetcher):
        self._fetcher = fetcher
        self._path = path
        self._shelf = None

    def __call__(self, rjcode: str) -> 'WorkInfo':
        try:
            return self._shelf[rjcode]
        except KeyError:
            work_info = self._fetcher(rjcode)
            self._shelf[rjcode] = work_info
            return work_info
        except TypeError:
            raise ValueError('called unopened CachedFetcher')

    def __enter__(self):
        self._shelf = shelve.open(self._path)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        self._shelf.close()


_CACHE = Path.home() / '.cache' / 'mir.dlsite.db'


def get_fetcher():
    """Get default cached fetcher."""
    path = Path(_CACHE)
    path.parent.mkdir(parents=True, exist_ok=True)
    return CachedFetcher(_CACHE, fetch_work)
