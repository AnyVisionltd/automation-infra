import io
import av


class PyAv(object):
    def __init__(self, video):
        self._video = video
        self._file = self._stream_file()

    def _stream_file(self):
        with io.BytesIO(self._video) as data, av.open(data) as file:
            file_data = file.streams[0]
        return file_data

    def duration(self):
        return float(self._file.duration * self._file.time_base)

    def codec_context(self):
        return self._file.codec_context
