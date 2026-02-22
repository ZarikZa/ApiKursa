import time
import logging
from django.core.files.uploadhandler import TemporaryFileUploadHandler

logger = logging.getLogger("uploadwire")

class DebugUploadHandler(TemporaryFileUploadHandler):
    """
    Логирует приходящие чанки тела запроса на уровне Django upload handlers.
    Это ТО место, где видно: реально ли приходят байты с телефона.
    """

    def __init__(self, request=None):
        super().__init__(request)
        self._t0 = time.time()
        self._total = 0
        self._last = 0
        self._last_t = self._t0

    def new_file(self, *args, **kwargs):
        logger.warning("[UPH] new_file args=%s kwargs=%s", args, kwargs)
        return super().new_file(*args, **kwargs)

    def receive_data_chunk(self, raw_data, start):
        now = time.time()
        self._total += len(raw_data)

        # лог раз в ~256KB или раз в 1 сек
        if self._total - self._last >= 256 * 1024 or (now - self._last_t) >= 1.0:
            speed = (self._total / max(0.001, now - self._t0)) / (1024 * 1024)
            logger.warning("[UPH] recv total=%d bytes (%.2f MB) start=%d speed=%.2f MB/s",
                           self._total, self._total/1024/1024, start, speed)
            self._last = self._total
            self._last_t = now

        return super().receive_data_chunk(raw_data, start)

    def file_complete(self, file_size):
        now = time.time()
        logger.warning("[UPH] file_complete size=%d bytes time=%.2fs",
                       file_size, now - self._t0)
        return super().file_complete(file_size)
