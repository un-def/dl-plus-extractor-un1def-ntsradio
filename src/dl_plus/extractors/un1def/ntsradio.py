from datetime import datetime
from urllib.parse import urljoin

from dl_plus.extractor import Extractor, ExtractorError, ExtractorPlugin


__version__ = '0.1.0'


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

    def _real_extract(self, url):
        show_id, episode_id = self.dlp_match(
            url).group('show_id', 'episode_id')
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
        for source in episode['audio_sources']:
            if source['source'] == 'mixcloud':
                result['url'] = source['url']
                result['ie_key'] = 'Mixcloud'
                break
        else:
            result['url'] = episode['audio_sources'][0]['url']
        return result
