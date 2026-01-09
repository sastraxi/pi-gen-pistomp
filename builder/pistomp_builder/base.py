from contextvars import ContextVar
from abc import ABC
import subprocess
from pathlib import Path
from contextlib import contextmanager
import contextvars
import os
import shlex
import tempfile
import time

_is_superuser = contextvars.ContextVar("is_superuser", default=False)
_ssh_target: ContextVar["SshContext" | None] = contextvars.ContextVar(
    "ssh_target", default=None
)


@contextmanager
def superuser():
    """Context manager to execute commands with sudo privileges."""
    token = _is_superuser.set(True)
    try:
        yield
    finally:
        _is_superuser.reset(token)


class SshContext:
    def __init__(self, host: str):
        self.host: str = host
        self.control_path: Path = (
            Path(tempfile.gettempdir()) / f"ssh_mux_{os.getpid()}_{time.time()}"
        )

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
        _ssh_target.reset(self.token)
        if self.control_path.exists():
            try:
                self.control_path.unlink()
            except:  # noqa: E722
                pass

    def get_cmd_prefix(self) -> list[str]:
        return ["ssh", "-S", str(self.control_path), self.host]


@contextmanager
def ssh_connection(host: str):
    with SshContext(host) as ctx:
        yield ctx


def run_cmd(
    cmd: str | list[str],
    cwd: Path | None = None,
    check: bool = True,
    shell: bool = False,
    env: dict[str, str] | None = None,
    capture_output: bool = False,
    text: bool = False,
) -> subprocess.CompletedProcess:
    ssh_ctx = _ssh_target.get()

    # Normalize cmd to string for display/processing if it's a list (unless we keep it list for subprocess)
    # SSH commands typically need a single string or careful quoting.
    # If list, we rely on subprocess to quote args LOCALLY.
    # For REMOTE, we generally pass a single string to 'ssh host "cmd"'

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

        # Shell=True doesn't apply to the local ssh command invocation usually,
        # but the remote side executes in a shell.
        return subprocess.run(
            full_cmd,
            check=check,
            capture_output=capture_output,
            text=text or (capture_output and True),  # Assume text if capturing mostly
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


# --- File System Abstractions ---


class fs:
    @staticmethod
    def exists(path: Path | str) -> bool:
        """Check if path exists (local or remote)."""
        cmd = f"test -e {path}"
        # run_cmd will handle remote/local dispatch
        # We need check=False so we can read return code
        ret = run_cmd(cmd, check=False, shell=True)
        return ret.returncode == 0

    @staticmethod
    def mkdir(path: Path | str, parents: bool = True, exist_ok: bool = True):
        """Create directory."""
        flags = []
        if parents:
            flags.append("-p")
        # exist_ok is implied by -p usually, but explicit check might be needed if strict
        # 'mkdir -p' is usually what we want
        cmd = f"mkdir {' '.join(flags)} {path}"
        run_cmd(cmd, shell=True)

    @staticmethod
    def chown(
        path: Path | str, user: str, group: str | None = None, recursive: bool = False
    ):
        """Change ownership."""
        flags = "-R" if recursive else ""
        owner = f"{user}:{group}" if group else user
        cmd = f"chown {flags} {owner} {path}"
        # Often requires sudo, caller should use context or we assume?
        # Let's just run it, run_cmd handles context.
        run_cmd(cmd, shell=True)

    @staticmethod
    def install(src: Path | str, dest: Path | str, mode: str = "644"):
        """Install file (copy)."""
        # If we are remote, src must be remote path?
        # Caller handles syncing src to remote temp first if needed.
        run_cmd(f"install -m {mode} {src} {dest}", shell=True)


def get_env_var(name: str, default: str = "") -> str:
    """
    Get an environment variable from the target environment (local or remote).
    """
    if _ssh_target.get():
        # Remote
        try:
            # We must use 'bash -c' or similar to ensure variable expansion happens
            # But run_cmd usually executes command.
            # 'echo $VAR' might be expanded by LOCAL shell if not careful.
            # We want REMOTE expansion.
            # Single quotes prevent local expansion: 'echo $VAR'
            # But ssh arguments are concatenated.
            # Best is: run_cmd(['bash', '-c', f'echo "${name}"'], ...)
            # Or simplified: echo ${name}

            # Note: run_cmd takes list or string.
            # If we pass list: ['echo', f'${name}'] -> ssh host echo $name
            # If we pass string: f'echo ${name}' -> ssh host echo $name

            # To be safe against local expansion, we rely on how we invoke run_cmd or the fact that python strings don't expand $VAR automatically.

            proc = run_cmd(
                f'echo "${name}"',
                capture_output=True,
                text=True,
                check=False,  # Don't fail if empty
            )
            if proc.returncode == 0:
                return proc.stdout.strip()
            return default
        except Exception:
            return default
    else:
        # Local
        return os.environ.get(name, default)


def is_chroot() -> bool:
    """
    Check if systemd is active.
    """
    try:
        # We need to capture output/suppress stderr to avoid noise
        # And use run_cmd so it checks REMOTE if needed
        run_cmd(
            "systemctl list-units --no-legend --max=0",
            check=True,
            shell=True,
            capture_output=True,
        )
        return False
    except subprocess.CalledProcessError:
        return True


def manage_service(service: str, action: str):
    """
    Manage a systemd service (start, stop, restart).
    """
    if is_chroot():
        print(f"Chroot/No-Systemd detected. Skipping {action} for {service}.")
        return

    print(f"{action.capitalize()}ing {service}...")
    with superuser():
        run_cmd(f"systemctl {action} {service}", check=False, shell=True)


class Component(ABC):
    name: str
    repo_url: str | None = None
    default_branch: str | None = None
    persistent_repo_path: Path | None = None
    services: list[str] = []

    def build_and_install(self, source_dir: Path) -> None:  # pyright: ignore[reportUnusedParameter]
        raise NotImplementedError
