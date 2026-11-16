#!/usr/bin/env python3
"""Hold the shared operations lock for a complete script tree; never evaluate a shell string."""

import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import uuid

BUSY = 75


def is_alive(pid):
    if os.name != "nt":
        try:
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            return False
    # os.kill(pid, 0) terminates processes on Windows; query the process handle instead.
    import ctypes
    from ctypes import wintypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.OpenProcess(0x1000, False, pid)
    if not handle:
        return ctypes.get_last_error() == 5
    try:
        code = wintypes.DWORD()
        return not kernel.GetExitCodeProcess(handle, ctypes.byref(code)) or code.value == 259
    finally:
        kernel.CloseHandle(handle)


def lock(stream):
    stream.seek(0)
    if os.name == "nt":
        import msvcrt

        msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
    else:
        import fcntl

        fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)


def atomic_json(path, data):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data), encoding="utf-8")
    os.replace(temporary, path)


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ready-file", type=Path)
    parser.add_argument("--read-only", action="store_true")
    parser.add_argument("--check-lock", action="store_true")
    parser.add_argument("--command-env", action="store_true")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command
    if args.command_env:
        try:
            count = int(os.environ.pop("EVS_OPS_COMMAND_ARGC"))
            if not 1 <= count <= 102:
                parser.error("invalid command argument count")
            command = [os.environ.pop(f"EVS_OPS_COMMAND_ARG_{index}") for index in range(count)]
        except (KeyError, ValueError):
            parser.error("invalid command argument environment")
    if command[:1] == ["--"]:
        command = command[1:]
    if not command and not args.check_lock:
        parser.error("a command array is required")
    state = Path(os.environ.get("OPS_STATE_DIR", str(Path(__file__).resolve().parents[1] / "var")))
    state.mkdir(parents=True, exist_ok=True)
    lock_path = state / "mutation.lock"
    owner_path = state / "mutation-owner.json"
    token = os.environ.get("EVS_OPS_LOCK_TOKEN")
    inherited = False
    if token and owner_path.exists():
        try:
            owner = json.loads(owner_path.read_text(encoding="utf-8"))
            inherited = is_alive(owner["pid"]) and owner["token"] == token
        except (OSError, ValueError, KeyError):
            pass
    if args.check_lock:
        return 0 if inherited else 1
    handle = None
    if not args.read_only and not inherited:
        handle = lock_path.open("a+b")
        if lock_path.stat().st_size == 0:
            handle.write(b"0")
            handle.flush()
        try:
            lock(handle)
        except OSError:
            if args.ready_file:
                atomic_json(args.ready_file, {"state": "BUSY"})
            print("ERROR: another data-changing operation is running", file=sys.stderr)
            return BUSY
        # A dead supervisor must not allow a still-running worker to be overlapped.
        if owner_path.exists():
            previous = json.loads(owner_path.read_text(encoding="utf-8"))
            worker_pid = previous.get("workerPid")
            if worker_pid:
                if is_alive(worker_pid):
                    if args.ready_file:
                        atomic_json(args.ready_file, {"state": "BUSY"})
                    print("ERROR: previous worker still exists; reconcile it before loading", file=sys.stderr)
                    return BUSY
        token = uuid.uuid4().hex
        os.environ["EVS_OPS_LOCK_TOKEN"] = token
        atomic_json(owner_path, {"token": token, "pid": os.getpid()})
    child = None
    interrupted = False
    shutdown_deadline = None

    def signal_group(signum):
        try:
            os.killpg(child.pid, signum)
        except ProcessLookupError:
            pass

    def group_alive():
        try:
            os.killpg(child.pid, 0)
            return True
        except ProcessLookupError:
            return False

    def stop(signum, frame):
        nonlocal interrupted, shutdown_deadline
        interrupted = True
        if shutdown_deadline is None:
            shutdown_deadline = time.monotonic() + 10
        if child is not None:
            if os.name != "nt":
                signal_group(signal.SIGTERM)
            elif child.poll() is None:
                subprocess.run(["taskkill", "/PID", str(child.pid), "/T", "/F"], check=False)

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        # Shell scripts are always invoked via the configured Bash executable.
        environment = os.environ.copy()
        if os.name == "nt" and Path(command[0]).name.lower() in ("bash", "bash.exe"):
            environment["EVS_OPS_EXEC_ARGC"] = str(len(command) - 1)
            for index, argument in enumerate(command[1:]):
                environment[f"EVS_OPS_EXEC_ARG_{index}"] = argument
            command = [command[0], Path(__file__).with_name("process_exec.sh").as_posix()]
        child = subprocess.Popen(command, env=environment, start_new_session=os.name != "nt")
        if handle:
            atomic_json(owner_path, {"token": token, "pid": os.getpid(), "workerPid": child.pid})
        if args.ready_file:
            atomic_json(args.ready_file, {"state": "RUNNING", "workerPid": child.pid})
        if interrupted:
            stop(signal.SIGTERM, None)
        while True:
            exited = child.poll() is not None
            if interrupted and os.name != "nt":
                # The worker may exit before a descendant that ignores SIGTERM.
                # Hold the lock until the entire group has stopped or been killed.
                if group_alive():
                    if time.monotonic() >= shutdown_deadline:
                        signal_group(signal.SIGKILL)
                        child.wait()
                        break
                elif exited:
                    break
            elif exited:
                break
            elif interrupted and time.monotonic() >= shutdown_deadline:
                subprocess.run(["taskkill", "/PID", str(child.pid), "/T", "/F"], check=False)
            time.sleep(0.05)
        return 130 if interrupted else child.returncode
    finally:
        if handle:
            owner_path.unlink(missing_ok=True)
            handle.close()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError) as error:
        print(f"ERROR: process supervisor: {error}", file=sys.stderr)
        sys.exit(1)
