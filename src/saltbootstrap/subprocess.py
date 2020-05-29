import errno
import logging
import os
import select
import subprocess
import sys
import tempfile
import time
import weakref
from time import monotonic as _time

_mswindows = sys.platform == "win32"


try:
    from win32file import ReadFile, WriteFile
    from win32pipe import PeekNamedPipe
    import msvcrt
except ImportError:
    import fcntl

log = logging.getLogger(__name__)

# The hacks we go through to be able to send a subprocess output for both stdXXX and a log file...


class Popen(subprocess.Popen):
    def __init__(self, *args, **kwargs):
        for key in ("stdout", "stderr"):
            if key in kwargs:
                raise RuntimeError(
                    "{}.Popen() does not accept {} as a valid keyword argument".format(
                        __name__, key
                    )
                )
        # Half a megabyte in memory is more than enough to start writing to
        # a temporary file.
        stdout = tempfile.SpooledTemporaryFile(512000, mode="w", encoding="utf-8")
        kwargs["stdout"] = subprocess.PIPE
        stderr = tempfile.SpooledTemporaryFile(512000, mode="w", encoding="utf-8")
        kwargs["stderr"] = subprocess.PIPE
        super().__init__(*args, **kwargs)
        self._stdout = stdout
        self._stderr = stderr
        weakref.finalize(self, stdout.close)
        weakref.finalize(self, stderr.close)

    def recv(self, maxsize=None):
        return self._recv("stdout", maxsize)

    def recv_err(self, maxsize=None):
        return self._recv("stderr", maxsize)

    def send_recv(self, input="", maxsize=None):
        return self.send(input), self.recv(maxsize), self.recv_err(maxsize)

    def get_conn_maxsize(self, which, maxsize):
        if maxsize is None:
            maxsize = 1024
        elif maxsize < 1:
            maxsize = 1
        return getattr(self, which), maxsize

    def _close(self, which):
        getattr(self, which).close()
        setattr(self, which, None)

    if _mswindows:

        def send(self, input):
            if not self.stdin:
                return None

            try:
                x = msvcrt.get_osfhandle(self.stdin.fileno())
                (errCode, written) = WriteFile(x, input)
                # self._stdin_logger.debug(input.rstrip())
            except ValueError:
                return self._close("stdin")
            except (subprocess.pywintypes.error, Exception) as why:
                if why.args[0] in (109, errno.ESHUTDOWN):
                    return self._close("stdin")
                raise

            return written

        def _recv(self, which, maxsize):
            conn, maxsize = self.get_conn_maxsize(which, maxsize)
            if conn is None:
                return None

            try:
                x = msvcrt.get_osfhandle(conn.fileno())
                (read, nAvail, nMessage) = PeekNamedPipe(x, 0)
                if maxsize < nAvail:
                    nAvail = maxsize
                if nAvail > 0:
                    (errCode, read) = ReadFile(x, nAvail, None)
            except ValueError:
                return self._close(which)
            except (subprocess.pywintypes.error, Exception) as why:
                if why.args[0] in (109, errno.ESHUTDOWN):
                    return self._close(which)
                raise

            read = read.replace("\r\n", "\n").replace("\r", "\n")

            getattr(self, f"_{which}").write(read)
            getattr(sys, which).write(read)
            return read

    else:

        def send(self, input):
            if not self.stdin:
                return None

            if not select.select([], [self.stdin], [], 0)[1]:
                return 0

            try:
                written = os.write(self.stdin.fileno(), input)
                # self._stdin_logger.debug(input.rstrip())
            except OSError as why:
                if why.args[0] == errno.EPIPE:  # broken pipe
                    return self._close("stdin")
                raise

            return written

        def _recv(self, which, maxsize):
            conn, maxsize = self.get_conn_maxsize(which, maxsize)
            if conn is None:
                return None

            flags = fcntl.fcntl(conn, fcntl.F_GETFL)
            if not conn.closed:
                fcntl.fcntl(conn, fcntl.F_SETFL, flags | os.O_NONBLOCK)

            try:
                if not select.select([conn], [], [], 0)[0]:
                    return ""

                buff = conn.read(maxsize)
                if not buff:
                    return self._close(which)

                buff = buff.replace("\r\n", "\n").replace("\r", "\n")

                getattr(self, f"_{which}").write(buff)
                getattr(sys, which).write(buff)
                return buff
            finally:
                if not conn.closed:
                    fcntl.fcntl(conn, fcntl.F_SETFL, flags)

    def communicate(self, input=None, timeout=None):
        super().communicate(input=input, timeout=timeout)
        self._stdout.flush()
        self._stdout.seek(0)
        self._stderr.flush()
        self._stderr.seek(0)
        return self._stdout.read(), self._stderr.read()

    def poll(self, *args, **kwargs):
        self.recv()
        self.recv_err()
        return super().poll(*args, **kwargs)


def run(*popenargs, input=None, capture_output=False, timeout=None, check=False, **kwargs):
    """Run command with arguments and return a CompletedProcess instance.
    The returned instance will have attributes args, returncode, stdout and
    stderr. By default, stdout and stderr are not captured, and those attributes
    will be None. Pass stdout=PIPE and/or stderr=PIPE in order to capture them.
    If check is True and the exit code was non-zero, it raises a
    CalledProcessError. The CalledProcessError object will have the return code
    in the returncode attribute, and output & stderr attributes if those streams
    were captured.
    If timeout is given, and the process takes too long, a TimeoutExpired
    exception will be raised.
    There is an optional argument "input", allowing you to
    pass bytes or a string to the subprocess's stdin.  If you use this argument
    you may not also use the Popen constructor's "stdin" argument, as
    it will be used internally.
    By default, all communication is in bytes, and therefore any "input" should
    be bytes, and the stdout and stderr will be bytes. If in text mode, any
    "input" should be a string, and stdout and stderr will be strings decoded
    according to locale encoding, or by "encoding" if set. Text mode is
    triggered by setting any of text, encoding, errors or universal_newlines.
    The other arguments are the same as for the Popen constructor.
    """
    log.info(f"Running: '{' '.join(*popenargs)}'")
    if input is not None:
        if kwargs.get("stdin") is not None:
            raise ValueError("stdin and input arguments may not both be used.")
        kwargs["stdin"] = subprocess.PIPE

    if capture_output:
        if kwargs.get("stdout") is not None or kwargs.get("stderr") is not None:
            raise ValueError("stdout and stderr arguments may not be used " "with capture_output.")
        kwargs["stdout"] = subprocess.PIPE
        kwargs["stderr"] = subprocess.PIPE

    with Popen(*popenargs, **kwargs) as process:
        if timeout:
            endtimeout = _time() + timeout
        try:
            while process.poll() is None:
                if timeout is not None:
                    if _time() >= endtimeout:
                        # Force a TimeoutExpired to raise
                        process.wait(timeout=0)
                time.sleep(0.025)
        except subprocess.TimeoutExpired as exc:
            process.kill()
            if _mswindows:
                # Windows accumulates the output in a single blocking
                # read() call run on child threads, with the timeout
                # being done in a join() on those threads.  communicate()
                # _after_ kill() is required to collect that and add it
                # to the exception.
                exc.stdout, exc.stderr = process.communicate()
            else:
                # POSIX _communicate already populated the output so
                # far into the TimeoutExpired exception.
                process.wait()
            raise
        except:  # noqa: E722 - Including KeyboardInterrupt, communicate handled that.
            process.kill()
            # We don't call process.wait() as .__exit__ does that for us.
            raise
        retcode = process.poll()
        stdout, stderr = process.communicate()
        if check and retcode:
            raise subprocess.CalledProcessError(retcode, process.args, output=stdout, stderr=stderr)
    return subprocess.CompletedProcess(process.args, retcode, stdout, stderr)


def __getattr__(attrname):
    if attrname == "run":
        return run
    if attrname == "Popen":
        return Popen
    return getattr(subprocess, attrname)
