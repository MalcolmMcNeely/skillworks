# Handed in rather than read from the machine, so a test holds time still and moves it on purpose.

import threading
from datetime import datetime, timezone


class Clock:
    def now(self):
        return datetime.now(timezone.utc)

    # A daemon thread, so a driver that dies is never kept alive by its own heartbeat.
    def every(self, seconds, do):
        ended = threading.Event()

        def beat():
            while not ended.wait(seconds):
                do()

        thread = threading.Thread(target=beat, daemon=True)
        thread.start()

        def stop():
            ended.set()
            if thread is not threading.current_thread():
                thread.join()
        return stop
