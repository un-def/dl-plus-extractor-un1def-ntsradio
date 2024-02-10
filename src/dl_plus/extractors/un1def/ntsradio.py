from datetime import datetime
from urllib.parse import urljoin

from dl_plus import ytdl
from dl_plus.extractor import Extractor, ExtractorError, ExtractorPlugin


try_get = ytdl.import_from('utils', 'try_get')


__version__ = '0.2.0'


plugin = ExtractorPlugin(__name__)


class NTSRadioBaseExtractor(Extractor):

    DLP_BASE_URL = r'https?://(?:www\.)?nts\.live'

    _API_BASE = 'https://www.nts.live/api/v2/'

    def _fetch(self, *path, description, item_id, **kwargs):
        """
        Fetch the resource using NTS API.

        The positional arguments are the parts of the resource path relative
        to the _API_BASE.

        The following keyword arguments are required by this method:
            * item_id -- item identifier (for logging purposes).
            * description -- human-readable resource description (for logging
            purposes).

        Any additional keyword arguments are passed directly to
        the _download_json method.
        """
        response = self._download_json(
            urljoin(self._API_BASE, '/'.join(path)),
            item_id,
            note=f'Downloading {description} metadata',
            errnote=f'Unable to download {description} metadata',
            **kwargs,
        )
        if not isinstance(response, dict):
            raise ExtractorError(f'JSON object expected, got: {response!r}')
        error = response.get('error')
        if error:
            raise ExtractorError(
                f'{self.IE_NAME} returned error: {error}', expected=True)
        return response


@plugin.register('episode')
class NTSRadioEpisodeExtractor(NTSRadioBaseExtractor):

    DLP_REL_URL = (
        r'/shows/(?P<show_id>[^/#?]+)/episodes/(?P<episode_id>[^/#?]+)')

    _AUDIO_SOURCE_IE_KEY_MAP = {
        'mixcloud': 'Mixcloud',
        'soundcloud': 'Soundcloud',
    }

    def _real_extract(self, url):
        show_id, episode_id = self._match_valid_url(url).group(
            'show_id', 'episode_id')
        episode = self._fetch(
            'shows', show_id, 'episodes', episode_id,
            item_id=episode_id, description='episode',
        )
        broadcast_datetime = datetime.fromisoformat(episode['broadcast'])
        title = '{name}, {location}, {date}'.format(
            name=episode['name'].strip(),
            location=episode['location_long'],
            date=broadcast_datetime.strftime('%d.%m.%y'),
        )
        result = {
            '_type': 'url_transparent',
            'title': title,
            'description': episode['description'],
            'genre': ', '.join(g['value'] for g in episode['genres']),
        }
        if mixcloud_url := episode.get('mixcloud'):
            result['url'] = mixcloud_url
            result['ie_key'] = 'Mixcloud'
        elif audio_source := try_get(episode, lambda e: e['audio_sources'][0]):
            result['url'] = audio_source['url']
            result['ie_key'] = self._AUDIO_SOURCE_IE_KEY_MAP.get(
                audio_source['source'])
        else:
            raise ExtractorError('no audio sources', expected=True)
        return result
