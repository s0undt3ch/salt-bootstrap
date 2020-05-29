import copy
import io
import logging
import pathlib
import re
import sys
from collections import deque

from blessings import Terminal

# Add a NullHandler to avoid logging warnings
logging.root.addHandler(logging.NullHandler())

# 7-bit C1 ANSI sequences
ANSI_ESCAPE = re.compile(
    r"""
    \x1B  # ESC
    (?:   # 7-bit C1 Fe (except CSI)
        [@-Z\\-_]
    |     # or [ for CSI, followed by a control sequence
        \[
        [0-?]*  # Parameter bytes
        [ -/]*  # Intermediate bytes
        [@-~]   # Final byte
    )
""",
    re.VERBOSE,
)

LOG_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
}


class ConsoleFormatter(logging.Formatter):
    def __init__(self, term):
        super().__init__("%(message)s")
        self.colors = {
            logging.DEBUG: term.cyan,
            logging.INFO: term.normal,
            logging.WARNING: term.yellow,
            logging.ERROR: term.red,
            logging.CRITICAL: term.magenta,
            "normal": term.normal,
        }

    def format(self, record):
        if record.levelno not in self.colors:
            # We don't know how to handle this color, super fallback
            return super().format(record)
        # Only modify a copy of the record
        record = copy.copy(record)
        record.msg = f"{self.colors[record.levelno]}{record.msg}{self.colors['normal']}"
        return super().format(record)


class TemporaryLoggingHandler(logging.NullHandler):
    """
    This logging handler will store all the log records up to its maximum
    queue size at which stage the first messages stored will be dropped.

    Should only be used as a temporary logging handler, while the logging
    system is not fully configured.

    Once configured, pass any logging handlers that should have received the
    initial log messages to the function
    :func:`TemporaryLoggingHandler.sync_with_handlers` and all stored log
    records will be dispatched to the provided handlers.

    """

    def __init__(self, level=logging.NOTSET, max_queue_size=10000):
        self.__max_queue_size = max_queue_size
        super().__init__(level=level)
        self.__messages = deque(maxlen=max_queue_size)

    def handle(self, record):
        self.acquire()
        self.__messages.append(record)
        self.release()

    def sync_with_handlers(self, *handlers):
        """
        Sync the stored log records to the provided log handlers.
        """
        if not handlers:
            return

        while self.__messages:
            record = self.__messages.popleft()
            for handler in handlers:
                if handler.level > record.levelno:
                    # If the handler's level is higher than the log record one,
                    # it should not handle the log record
                    continue
                handler.handle(record)


TEMP_LOGGING_HANDLER = TemporaryLoggingHandler()
logging.root.addHandler(TEMP_LOGGING_HANDLER)


class STDWrapper(io.TextIOWrapper):
    def __init__(self, buff, logfile):
        super().__init__(buff, encoding="utf-8", errors="backslashreplace", line_buffering=True)
        self._logfile = logfile

    def write(self, data):
        log_data = ANSI_ESCAPE.sub("", data)
        if self._logfile is not None:
            self._logfile.write(log_data)
            self._logfile.flush()
        return super().write(data)


def setup_logging(log_level: str, term: Terminal):
    levelno = LOG_LEVELS.get(log_level, logging.INFO)
    logging.root.setLevel(levelno)
    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(levelno)
    handler.setFormatter(ConsoleFormatter(term))
    logging.root.addHandler(handler)
    logging.root.removeHandler(TEMP_LOGGING_HANDLER)
    TEMP_LOGGING_HANDLER.sync_with_handlers(handler)


def patch_stds(logfile: pathlib.Path) -> None:
    # Patch python's std's so that any output is also written to a log file
    sys.stdout = sys.__stdout__ = STDWrapper(sys.stdout.detach(), logfile)  # type: ignore[attr-defined]
    sys.stderr = sys.__stderr__ = STDWrapper(sys.stderr.detach(), logfile)  # type: ignore[attr-defined]
