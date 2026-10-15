import os
import subprocess
import sys

# PyInstaller variables that make a child process re-use the *parent's*
# extraction folder / environment.  If they leak into the restarted copy it
# starts half-broken (missing DLLs, charts and icons gone) and the temp folder
# cannot be deleted afterwards ("Failed to remove temporary directory _MEI...").
_PYI_VARS = ("_MEIPASS2", "_PYI_APPLICATION_HOME_DIR", "_PYI_ARCHIVE_FILE",
             "_PYI_PARENT_PROCESS_LEVEL", "_PYI_LINUX_PROCESS_NAME")


def restart_app():
    """Start a fresh copy of the application and close this one."""

    env = os.environ.copy()
    for name in _PYI_VARS:
        env.pop(name, None)

    if getattr(sys, "frozen", False):
        command = [sys.executable]
        env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"   # PyInstaller >= 6.9
        cwd = os.path.dirname(sys.executable)
    else:
        command = [sys.executable] + sys.argv
        cwd = None

    flags = 0
    if os.name == "nt":
        flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP

    subprocess.Popen(command, env=env, cwd=cwd, close_fds=True, creationflags=flags)

    os._exit(0)
