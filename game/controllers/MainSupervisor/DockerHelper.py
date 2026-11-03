from __future__ import annotations
from typing import TYPE_CHECKING
from typing import Optional

from ConsoleLog import Console
import subprocess
import os
from threading import Thread

if TYPE_CHECKING:
    from MainSupervisor import Erebus

EREBUS_CONTROLLER_TAG = "erebus_internal"

def _docker_available() -> bool:
    """Require a running Docker daemon; the project's Dockerfile chooses its base."""
    try:
        result = subprocess.run(["docker", "info", "--format", "{{.ServerVersion}}"],
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                timeout=15, check=False)
        return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired) as error:
        Console.log_err(f"Docker is unavailable: {error}")
        return False

def run_docker_container(
    erebus: Erebus, 
    project_dir: str,
) -> Optional[subprocess.Popen] | None:
    """Run a controller via a docker container

    Args:
        project_dir (str): System path to directory containing a Dockerfile

    Returns:
        Optional[subprocess.Popen]: Subprocess if docker container runs 
        successfully, None otherwise.
    """
    if not _docker_available():
        Console.log_err("Docker is not running. Start Docker and try again.")
        return None
    host = os.environ.get("EREBUS_DOCKER_HOST", "host.docker.internal")
    port = os.environ.get("EREBUS_CONTROLLER_PORT", "1234")
    if not port.isdecimal() or not 1 <= int(port) <= 65535:
        Console.log_err("EREBUS_CONTROLLER_PORT must be a TCP port from 1 to 65535.")
        return None

    # Build container
    try:
        command: list[str] = ["docker", "build", 
                              "--tag" ,EREBUS_CONTROLLER_TAG, project_dir]
        Console.log_info(f"Building project image ($ {' '.join(command)})")
        with subprocess.Popen(
            command,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
            bufsize=1, universal_newlines=True, shell=False, encoding="utf-8"
        ) as build_process:
            # Print output from build process
            if build_process.stdout:
                for line in build_process.stdout:
                    Console.log_info(line, sep=None, end='')
                    erebus.step(erebus.TIME_STEP)
                    
    except Exception as e:
        Console.log_err(f"Error building project image - {e}")
        return None
    
    if build_process.returncode != 0:
        Console.log_err(f"Unable to build project image")
        return None
    
    # Run container
    try:
        command: list[str] = ["docker", "run", 
                              "--add-host", "host.docker.internal:host-gateway",
                              "--env", f"EREBUS_SERVER={host}",
                              "--env", f"EREBUS_CONTROLLER_PORT={port}",
                              "--env", "EREBUS_ROBOT_NAME=Erebus_Bot", 
                              "--rm",
                              EREBUS_CONTROLLER_TAG]
        Console.log_info(f"Running container ($ {' '.join(command)})")
        run_process: subprocess.Popen = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            shell=False,
        )
        # Thread to print non-blocking stdout from docker container
        thread: Thread = Thread(target=print_stdout, args=[run_process.stdout])
        thread.daemon = True # thread dies with the program
        thread.start()
    except Exception as e:
        Console.log_err(f"Error running project image - {e}")
        return None
    
    return run_process

def print_stdout(out) -> None:
    """Print a sub process's stdout to the erebus console
    
    Used for printing docker container outputs to the console

    Args:
        out (IO[bytes]): Popen subprocess stdout bytes buffer
    """
    for line in iter(out.readline, b''):
        print(line.decode())
    out.close()