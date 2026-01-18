from contextvars import ContextVar
import subprocess
import shlex
import os
import contextvars
import tempfile
import time
from pathlib import Path
from contextlib import contextmanager
from typing import Optional, List, Union

# Context Variables
_is_superuser = contextvars.ContextVar("is_superuser", default=False)
_ssh_target: ContextVar["SshContext | None"] = contextvars.ContextVar(
    "ssh_target", default=None
)


class SshContext:
    def __init__(self, host: str):
        self.host: str = host
        self.control_path: Path = (
            Path(tempfile.gettempdir()) / f"ssh_mux_{os.getpid()}_{time.time()}"
        )
        self.token: Optional[contextvars.Token] = None

    def __enter__(self):
        # Start master connection
        print(f"Establishing SSH connection to {self.host}...")
        cmd = [
            "ssh",
            "-M",
            "-S",
            str(self.control_path),
            "-f",
            "-N",
            self.host,
        ]
        subprocess.run(cmd, check=True)
        self.token = _ssh_target.set(self)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Close master connection
        print("Closing SSH connection...")
        cmd = ["ssh", "-S", str(self.control_path), "-O", "exit", self.host]
        subprocess.run(
            cmd, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        if self.token:
            _ssh_target.reset(self.token)
        if self.control_path.exists():
            try:
                self.control_path.unlink()
            except OSError:
                pass

    def get_cmd_prefix(self) -> List[str]:
        return ["ssh", "-S", str(self.control_path), self.host]


@contextmanager
def ssh_connection(host: str):
    """Context manager to establish a persistent SSH connection."""
    with SshContext(host) as ctx:
        yield ctx


@contextmanager
def superuser():
    """Context manager to execute commands with sudo privileges."""
    token = _is_superuser.set(True)
    try:
        yield
    finally:
        _is_superuser.reset(token)


def run_cmd(
    cmd: Union[str, List[str]],
    cwd: Optional[Union[Path, str]] = None,
    check: bool = True,
    shell: bool = False,
    env: Optional[dict[str, str]] = None,
    capture_output: bool = False,
    text: bool = False,
) -> subprocess.CompletedProcess:
    ssh_ctx = _ssh_target.get()

    # Normalize cmd to string for display/processing if it's a list
    if isinstance(cmd, list):
        cmd_str = shlex.join(cmd)
    else:
        cmd_str = cmd

    # Handle Superuser
    if _is_superuser.get():
        if not cmd_str.strip().lstrip().startswith("sudo"):
            cmd_str = f"sudo {cmd_str}"

    # Handle CWD (inject cd)
    if cwd:
        cmd_str = f"cd {cwd} && {cmd_str}"

    if ssh_ctx:
        # Remote Execution
        full_cmd = ssh_ctx.get_cmd_prefix() + [cmd_str]
        print(f"Remote ({ssh_ctx.host}): {cmd_str}")

        if env:
            # SSH will inherit environment, but to set specific vars we need to prefix the command
            env_prefix = " ".join([f"{k}={shlex.quote(v)}" for k, v in env.items()])
            if cmd_str.startswith("sudo "):
                # If sudo is used: "sudo VAR=val cmd" works
                parts = cmd_str.split(" ", 1)
                cmd_str = f"{parts[0]} {env_prefix} {parts[1]}"
            else:
                cmd_str = f"{env_prefix} {cmd_str}"

            # Reconstruct full_cmd with updated string
            full_cmd = ssh_ctx.get_cmd_prefix() + [cmd_str]

        return subprocess.run(
            full_cmd,
            check=check,
            capture_output=capture_output,
            text=text or (capture_output and True),
        )
    else:
        # Local Execution
        print(f"Running: {cmd_str} (cwd={cwd})")

        # Merge env with current environment if provided
        final_env = os.environ.copy()
        if env:
            final_env.update(env)

        return subprocess.run(
            cmd_str if shell else shlex.split(cmd_str),
            cwd=cwd,
            check=check,
            shell=shell,
            env=final_env,
            capture_output=capture_output,
            text=text,
        )


def get_env_var(name: str, default: str = "") -> str:
    """
    Get an environment variable from the target environment (local or remote).
    """
    if _ssh_target.get():
        # Remote
        try:
            # Safely echo variable from remote shell
            proc = run_cmd(
                f'echo "${name}"',
                capture_output=True,
                text=True,
                check=False,
            )
            if proc.returncode == 0:
                return proc.stdout.strip()
            return default
        except Exception:
            return default
    else:
        # Local
        return os.environ.get(name, default)
