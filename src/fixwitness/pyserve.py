"""Faster DataFrame runs: import pandas or polars once, then fork a fresh process for every run.

Importing pandas takes about half a second, and a check makes hundreds of runs. The server
imports the libraries once and waits on a Unix socket. Each run is a tiny client process
(`python -m fixwitness.pyserve SOCKET -- <pyrun arguments>`) that sends its arguments, working
directory, environment and its own stdout/stderr to the server, which forks a child to do the run.

Each run is still isolated: the child is a new process (a copy of the server taken right after the
imports), it imports the user's script itself, and it exits when the run ends. The client's exit
code is the child's. A run that outlives its timeout is killed by an alarm in the child, and a
child whose client has gone away is killed too.

Not used for PySpark (a JVM can't be forked) or with --no-network (the child would not be in the
client's network namespace).
"""

from __future__ import annotations

import array
import json
import os
import socket
import sys
import threading


def _recv_all(conn: socket.socket) -> tuple[bytes, list[int]]:
    data, fds = b"", []
    while True:
        msg, anc, _, _ = conn.recvmsg(65536, socket.CMSG_SPACE(2 * array.array("i").itemsize))
        for level, kind, payload in anc:
            if level == socket.SOL_SOCKET and kind == socket.SCM_RIGHTS:
                a = array.array("i")
                a.frombytes(payload[: len(payload) - len(payload) % a.itemsize])
                fds += list(a)
        if not msg:
            break
        data += msg
        if data.endswith(b"\n"):
            break
    return data, fds


def _child(req: dict, fds: list[int]) -> None:
    """The forked child: becomes the run, then exits with its exit code."""
    try:
        os.setsid()
        if len(fds) == 2:
            os.dup2(fds[0], 1)
            os.dup2(fds[1], 2)
        devnull = os.open(os.devnull, os.O_RDONLY)
        os.dup2(devnull, 0)
        os.chdir(req["cwd"])
        os.environ.clear()
        os.environ.update(req["env"])
        if req.get("timeout"):
            import signal
            signal.signal(signal.SIGALRM, signal.SIG_DFL)
            signal.alarm(int(float(req["timeout"])) + 1)
        from fixwitness import pyrun
        code = pyrun.main(req["argv"])
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(code)
    except SystemExit as exc:
        os._exit(exc.code if isinstance(exc.code, int) else 1)
    except BaseException:
        import traceback
        traceback.print_exc()
        os._exit(2)


def _reply(conn: socket.socket, pid: int) -> None:
    watcher = threading.Thread(target=_watch_client, args=(conn, pid), daemon=True)
    watcher.start()
    try:
        _, status = os.waitpid(pid, 0)
        conn.sendall(f"{os.waitstatus_to_exitcode(status)}\n".encode())
    except OSError:
        pass
    finally:
        conn.close()


def _watch_client(conn: socket.socket, pid: int) -> None:
    """Kill the child if its client goes away (the runner killed it on a timeout)."""
    try:
        if conn.recv(1) == b"":
            os.killpg(pid, 9)
    except OSError:
        pass


def serve(path: str, preload: list[str]) -> None:
    import warnings
    warnings.simplefilter("ignore", DeprecationWarning)  # fork() while reply threads wait in syscalls
    for lib in preload:
        try:
            __import__(lib)
        except ImportError:
            pass
    from fixwitness import pyrun  # noqa: F401  (imported once, shared by every child)
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(path)
    srv.listen(64)
    print("ready", flush=True)
    while True:
        conn, _ = srv.accept()
        try:
            data, fds = _recv_all(conn)
            req = json.loads(data)
        except (OSError, ValueError):
            conn.close()
            continue
        pid = os.fork()  # from the main thread; the reply threads only wait in system calls
        if pid == 0:
            srv.close()
            _child(req, fds)
        for fd in fds:
            os.close(fd)
        threading.Thread(target=_reply, args=(conn, pid), daemon=True).start()


def client(path: str, argv: list[str]) -> int:
    timeout = os.environ.get("FIXWITNESS_RUN_TIMEOUT")
    req = json.dumps({"argv": argv, "cwd": os.getcwd(), "env": dict(os.environ),
                      "timeout": float(timeout) if timeout else None}).encode() + b"\n"
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.connect(path)
    s.sendmsg([req], [(socket.SOL_SOCKET, socket.SCM_RIGHTS, array.array("i", [1, 2]))])
    reply = b""
    while not reply.endswith(b"\n"):
        chunk = s.recv(64)
        if not chunk:
            return 2
        reply += chunk
    return int(reply)


class Server:
    """A running server for one check; `prefix` is the command that replaces `-m fixwitness.pyrun`."""

    def __init__(self, work, preload: list[str], env: dict):
        import subprocess
        self.path = str(work / "pyserve.sock")
        self.proc = subprocess.Popen([sys.executable, "-m", "fixwitness.pyserve", "--serve", self.path, *preload],
                                     stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=env,
                                     start_new_session=True)
        line = self.proc.stdout.readline()
        if line.strip() != b"ready":
            self.stop()
            raise RuntimeError("the DataFrame server did not start")

    def stop(self) -> None:
        try:
            os.killpg(self.proc.pid, 9)
        except OSError:
            pass
        self.proc.wait()
        if self.proc.stdout is not None:
            self.proc.stdout.close()


def main(argv: list[str]) -> int:
    if argv[:1] == ["--serve"]:
        serve(argv[1], argv[2:])
        return 0
    if len(argv) < 2 or argv[1] != "--":
        print("usage: python -m fixwitness.pyserve SOCKET -- <fixwitness.pyrun arguments>", file=sys.stderr)
        return 2
    return client(argv[0], argv[2:])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
