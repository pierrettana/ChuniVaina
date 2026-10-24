import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image

from branding import BASE, STEPS, welcome_if_needed
from song_notice import save_preferences, save_notice_preference, load_preferences, preferences_path


class ReleaseTests(unittest.TestCase):
    def test_tour_and_audio_preferences_preserve_each_other(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'preferences.json'
            save_notice_preference(True, path)
            save_preferences({'hide_welcome_tour': True}, path)
            save_notice_preference(False, path)
            self.assertEqual(load_preferences(path), {
                'hide_welcome_tour': True, 'hide_song_audio_notice': False})

    def test_startup_respects_tour_choice(self):
        with patch('song_notice.load_preferences', return_value={'hide_welcome_tour': True}), patch('branding.open_tutorial') as show:
            welcome_if_needed(object())
            show.assert_not_called()
        with patch('song_notice.load_preferences', return_value={}), patch('branding.open_tutorial') as show:
            app = object()
            welcome_if_needed(app)
            show.assert_called_once_with(app)

    def test_windows_preferences_use_appdata(self):
        with patch('song_notice.sys.platform', 'win32'), patch.dict('os.environ', {'APPDATA': '/example/roaming'}):
            self.assertEqual(preferences_path(), Path('/example/roaming/ChuniVaina/preferences.json'))

    def test_packaged_artwork_and_tutorial(self):
        self.assertEqual(len(STEPS), 7)
        for name in ('icon.png', 'mascot.png', 'ChuniVaina.icns', 'ChuniVaina.ico'):
            with Image.open(BASE/'assets'/name) as image:
                image.load()
                self.assertGreater(image.width, 0)
        with Image.open(BASE/'assets/icon.png') as image:
            self.assertEqual(image.size, (1024, 1024))


if __name__ == '__main__':
    unittest.main()
