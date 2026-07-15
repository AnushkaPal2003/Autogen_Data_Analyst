from autogen.coding import LocalCommandLineCodeExecutor


def build_executor(work_dir: str, timeout: int = 60):
    """
    Returns a code executor that runs the analyst's Python code as a local
    subprocess, scoped to its own working directory per analysis run.

    For untrusted or public-facing deployments, swap this for
    autogen.coding.DockerCommandLineCodeExecutor to run each execution in an
    isolated container instead of the host process.
    """
    return LocalCommandLineCodeExecutor(timeout=timeout, work_dir=work_dir)
