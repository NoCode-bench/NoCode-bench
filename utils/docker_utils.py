import tarfile
import threading
import os
import signal
import time
from pathlib import Path
import docker
from docker.models.containers import Container
import sys


HEREDOC_DELIMITER = "EOF_1399519320"  # different from dataset HEREDOC_DELIMITERs!

def copy_to_container(container: Container, src: Path, dst: Path):
    """
    Copy a file from local to a docker container

    Args:
        container (Container): Docker container to copy to
        src (Path): Source file path
        dst (Path): Destination file path in the container
    """
    # Check if destination path is valid
    if os.path.dirname(dst) == "":
        raise ValueError(
            f"Destination path parent directory cannot be empty!, dst: {dst}"
        )

    # temporary tar file
    tar_path = src.with_suffix(".tar")
    with tarfile.open(tar_path, "w") as tar:
        tar.add(
            src, arcname=dst.name
        )  # use destination name, so after `put_archive`, name is correct

    # get bytes for put_archive cmd
    with open(tar_path, "rb") as tar_file:
        data = tar_file.read()

    # Make directory if necessary
    container.exec_run(f"mkdir -p {dst.parent}")

    # Send tar file to container and extract
    container.put_archive(os.path.dirname(dst), data)

    # clean up in locally and in container
    tar_path.unlink()


def write_to_container(container: Container, data: str, dst: Path):
    """
    Write a string to a file in a docker container
    """
    # echo with heredoc to file
    command = f"cat <<'{HEREDOC_DELIMITER}' > {dst}\n{data}\n{HEREDOC_DELIMITER}"
    container.exec_run(command)

def exec_run_with_timeout(container: Container, cmd, workdir: str | None = None, timeout: int | None = 60):
    """
    Run a command in a container with a timeout.

    Args:
        container (docker.Container): Container to run the command in.
        cmd (str): Command to run.
        timeout (int): Timeout in seconds.
    """
    # Local variables to store the result of executing the command
    exec_result = b""
    exec_id = None
    exception = None
    timed_out = False

    # Wrapper function to run the command
    def run_command():
        nonlocal exec_result, exec_id, exception
        try:
            exec_id = container.client.api.exec_create(container.id, cmd, workdir=workdir)["Id"]
            exec_stream = container.client.api.exec_start(exec_id, stream=True)
            for chunk in exec_stream:
                exec_result += chunk
        except Exception as e:
            exception = e

    # Start the command in a separate thread
    thread = threading.Thread(target=run_command)
    start_time = time.time()
    thread.start()
    thread.join(timeout)

    if exception:
        raise exception

    # If the thread is still alive, the command timed out
    if thread.is_alive():
        if exec_id is not None:
            exec_pid = container.client.api.exec_inspect(exec_id)["Pid"]
            container.exec_run(f"kill -TERM {exec_pid}", detach=True)
        timed_out = True
    end_time = time.time()
    return exec_result.decode(), timed_out, end_time - start_time



def cleanup_container(client, container, logger=None):
    """
    Stop and remove a Docker container.
    Performs this forcefully if the container cannot be stopped with the python API.

    Args:
        client (docker.DockerClient): Docker client.
        container (docker.models.containers.Container): Container to remove.
        logger (logging.Logger): Logger to use for output. If None, print to stdout
    """
    if not container:
        return

    container_id = container.id

    # Attempt to stop the container
    try:
        if container:
            if logger:
                logger.info(f"Attempting to stop container {container.name}...")
            container.stop(timeout=15)
    except Exception as e:
        logger.error(
            f"Failed to stop container {container.name}: {e}. Trying to forcefully kill..."
        )
        try:
            # Get the PID of the container
            container_info = client.api.inspect_container(container_id)
            pid = container_info["State"].get("Pid", 0)

            # If container PID found, forcefully kill the container
            if pid > 0:
                if logger:
                    logger.info(
                        f"Forcefully killing container {container.name} with PID {pid}..."
                    )
                os.kill(pid, signal.SIGKILL)
            else:
                if logger:
                    logger.error(f"PID for container {container.name}: {pid} - not killing.")
        except Exception as e2:
            if logger:
                logger.error(
                    f"Failed to forcefully kill container {container.name}: {e2}\n"
                )

    # Attempt to remove the container
    try:
        if logger:
            logger.info(f"Attempting to remove container {container.name}...")
        container.remove(force=True)
        if logger:
            logger.info(f"Container {container.name} removed.")
    except Exception as e:
        if logger:
            logger.error(
                f"Failed to remove container {container.name}: {e}\n"
            )


def build_container(
    image_name,
    container_name,
    client: docker.DockerClient,
    logger,
    proxy=None
):
    """
    Builds the instance image for the given test spec and creates a container from the image.

    Args:
        test_spec (TestSpec): Test spec to build the instance image and container for
        client (docker.DockerClient): Docker client for building image + creating the container
        run_id (str): Run ID identifying process, used for the container name
        logger (logging.Logger): Logger to use for logging the build process
        nocache (bool): Whether to use the cache when building
        force_rebuild (bool): Whether to force rebuild the image even if it already exists
    """
    container = None
    try:
        container = client.containers.get(container_name)
        logger.info(f"Container '{container_name}' already exists.")
        return container
    except docker.errors.NotFound:
        try:
            # Create the container
            logger.info(f"Creating container for {container_name}...")
            env_config = {}
            
            if proxy:
                env_config.update({
                    'https_proxy': proxy,
                    'http_proxy': proxy
                })
            
            container = client.containers.create(
                image=image_name,
                name=container_name,
                user='root',
                detach=True,
                command="tail -f /dev/null",
                network_mode='host',
                environment=env_config
            )
            logger.info(f"Container for {container_name} created: {container.id}")
            return container
        except Exception as e:
            # If an error occurs, clean up the container and raise an exception
            logger.error(f"Error creating container for {container_name}: {e}")
            cleanup_container(client, container, logger)

