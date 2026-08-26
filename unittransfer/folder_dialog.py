"""Native Windows folder-picker dialog for the Settings "Browse..." button.

The UI is a browser page, and browsers deliberately never expose a real
filesystem path from an `<input type="file">` picker. But the server IS this
machine, so it can pop the OS's own folder dialog (`SHBrowseForFolderW`) and
hand the chosen path back over the API — the same trick a desktop app would
use, just triggered over HTTP instead of a local button handler.

ctypes + shell32 only (no tkinter): the portable build's embeddable Python
doesn't carry Tcl/Tk, but ctypes is always part of the stdlib.
"""
from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes
from typing import Optional

BIF_RETURNONLYFSDIRS = 0x0001
BIF_NEWDIALOGSTYLE = 0x0040


class _BROWSEINFO(ctypes.Structure):
    _fields_ = [
        ("hwndOwner", wintypes.HWND),
        ("pidlRoot", ctypes.c_void_p),
        ("pszDisplayName", wintypes.LPWSTR),
        ("lpszTitle", wintypes.LPCWSTR),
        ("ulFlags", wintypes.UINT),
        ("lpfn", ctypes.c_void_p),
        ("lParam", wintypes.LPARAM),
        ("iImage", ctypes.c_int),
    ]


# Explicit restype/argtypes: without them ctypes assumes a 32-bit int return,
# which truncates SHBrowseForFolderW's pointer on 64-bit Python and segfaults
# the moment it's dereferenced.
_shell32 = ctypes.windll.shell32
_ole32 = ctypes.windll.ole32
_shell32.SHBrowseForFolderW.restype = ctypes.c_void_p
_shell32.SHBrowseForFolderW.argtypes = [ctypes.POINTER(_BROWSEINFO)]
_shell32.SHGetPathFromIDListW.restype = wintypes.BOOL
_shell32.SHGetPathFromIDListW.argtypes = [ctypes.c_void_p, wintypes.LPWSTR]
_ole32.CoTaskMemFree.restype = None
_ole32.CoTaskMemFree.argtypes = [ctypes.c_void_p]


class _OPENFILENAMEW(ctypes.Structure):
    _fields_ = [
        ("lStructSize", wintypes.DWORD),
        ("hwndOwner", wintypes.HWND),
        ("hInstance", wintypes.HINSTANCE),
        ("lpstrFilter", wintypes.LPCWSTR),
        ("lpstrCustomFilter", wintypes.LPWSTR),
        ("nMaxCustFilter", wintypes.DWORD),
        ("nFilterIndex", wintypes.DWORD),
        ("lpstrFile", wintypes.LPWSTR),
        ("nMaxFile", wintypes.DWORD),
        ("lpstrFileTitle", wintypes.LPWSTR),
        ("nMaxFileTitle", wintypes.DWORD),
        ("lpstrInitialDir", wintypes.LPCWSTR),
        ("lpstrTitle", wintypes.LPCWSTR),
        ("Flags", wintypes.DWORD),
        ("nFileOffset", wintypes.WORD),
        ("nFileExtension", wintypes.WORD),
        ("lpstrDefExt", wintypes.LPCWSTR),
        ("lCustData", wintypes.LPARAM),
        ("lpfnHook", ctypes.c_void_p),
        ("lpTemplateName", wintypes.LPCWSTR),
        ("pvReserved", ctypes.c_void_p),
        ("dwReserved", wintypes.DWORD),
        ("FlagsEx", wintypes.DWORD),
    ]


OFN_FILEMUSTEXIST = 0x00001000
OFN_PATHMUSTEXIST = 0x00000800
OFN_EXPLORER = 0x00080000


# ---------------------------------------------------------------------------
# getting the dialog in front of the browser
#
# Every dialog here is opened by the SERVER process, which owns no window and
# never had the foreground: it is a background process answering an HTTP request
# the browser made. Windows refuses to hand the foreground to a process in that
# position (the foreground lock, `SetForegroundWindow` returning FALSE), so the
# dialog opened somewhere behind the browser window and, on most people's
# machines, as nothing but a flashing taskbar button — which reads exactly like
# "Browse... is stuck loading".
#
# The fix is to give the dialog an OWNER: a 0x0, never-painted popup this
# process does own. Two properties of ownership do the work. An owned window is
# always drawn above its owner, and a WS_EX_TOPMOST owner passes topmost on to
# it — so the dialog cannot end up behind the browser whatever the foreground
# lock says. Then, to make it the ACTIVE window rather than merely a visible one,
# the thread borrows the foreground thread's input state
# (`AttachThreadInput`) for the moment it takes to call `SetForegroundWindow`,
# which is the documented way out of the lock for a process that has a reason to
# be seen.
#
# It is created and destroyed around each dialog rather than kept: these calls
# arrive on whatever HTTP worker thread is free, and a window belongs to the
# thread that made it.

WS_POPUP = 0x80000000
WS_EX_TOPMOST = 0x00000008
WS_EX_TOOLWINDOW = 0x00000080

_user32 = ctypes.windll.user32
_user32.CreateWindowExW.restype = wintypes.HWND
_user32.CreateWindowExW.argtypes = [
    wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
    ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
    wintypes.HWND, wintypes.HMENU, wintypes.HINSTANCE, ctypes.c_void_p]
_user32.DestroyWindow.argtypes = [wintypes.HWND]
_user32.GetForegroundWindow.restype = wintypes.HWND
_user32.SetForegroundWindow.argtypes = [wintypes.HWND]
_user32.BringWindowToTop.argtypes = [wintypes.HWND]
_user32.GetWindowThreadProcessId.restype = wintypes.DWORD
_user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.c_void_p]
_user32.AttachThreadInput.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.BOOL]


class _Owner:
    """A hidden top-level window to hang a modal dialog off, as a context manager.

    ``with _Owner() as hwnd:`` — ``hwnd`` may be ``None`` (window creation is not
    worth failing a Browse over), and every dialog below already accepts a null
    owner, which is what it always used to pass.
    """

    def __enter__(self):
        self.hwnd = None
        try:
            # "STATIC" is a class the system has already registered, so there is
            # no window class of our own to register, name-clash or clean up.
            self.hwnd = _user32.CreateWindowExW(
                WS_EX_TOPMOST | WS_EX_TOOLWINDOW, "STATIC", "", WS_POPUP,
                0, 0, 0, 0, None, None, None, None)
        except OSError:
            self.hwnd = None
        if self.hwnd:
            _force_foreground(self.hwnd)
        return self.hwnd

    def __exit__(self, *exc):
        if self.hwnd:
            try:
                _user32.DestroyWindow(self.hwnd)
            except OSError:
                pass
        self.hwnd = None
        return False


def _force_foreground(hwnd) -> None:
    """Make ``hwnd`` the active window, borrowing the foreground thread's input.

    Best-effort throughout: if any of it is refused the dialog is still TOPMOST
    through its owner, which is the half that stops it hiding behind the browser.
    """
    try:
        fg = _user32.GetForegroundWindow()
        other = _user32.GetWindowThreadProcessId(fg, None) if fg else 0
        mine = ctypes.windll.kernel32.GetCurrentThreadId()
        attached = bool(other) and other != mine and bool(
            _user32.AttachThreadInput(mine, other, True))
        try:
            _user32.SetForegroundWindow(hwnd)
            _user32.BringWindowToTop(hwnd)
        finally:
            if attached:
                _user32.AttachThreadInput(mine, other, False)
    except OSError:
        pass


def browse_for_file(title: str = "Select a file", filter_spec: str = "",
                    initial_dir: str = "") -> Optional[str]:
    """Blocking native file-open dialog. Returns the chosen path or None.

    ``filter_spec`` is the Win32 double-NUL filter form, given here as
    ``"Meshes (*.mesh)|*.mesh|All files (*.*)|*.*"`` — the editor needs a real
    filesystem path for the mesh/texture to import, which a browser file input
    can never hand back.
    """
    if sys.platform != "win32":
        return None
    spec = filter_spec or "All files (*.*)|*.*"
    filt = "\0".join(spec.split("|")) + "\0\0"
    buf = ctypes.create_unicode_buffer(2048)
    ofn = _OPENFILENAMEW()
    ofn.lStructSize = ctypes.sizeof(_OPENFILENAMEW)
    ofn.lpstrFilter = filt
    ofn.lpstrFile = ctypes.cast(buf, wintypes.LPWSTR)
    ofn.nMaxFile = len(buf)
    ofn.lpstrTitle = title
    ofn.lpstrInitialDir = initial_dir or None
    ofn.Flags = OFN_FILEMUSTEXIST | OFN_PATHMUSTEXIST | OFN_EXPLORER
    comdlg32 = ctypes.windll.comdlg32
    comdlg32.GetOpenFileNameW.restype = wintypes.BOOL
    comdlg32.GetOpenFileNameW.argtypes = [ctypes.POINTER(_OPENFILENAMEW)]
    with _Owner() as owner:
        ofn.hwndOwner = owner
        if not comdlg32.GetOpenFileNameW(ctypes.byref(ofn)):
            return None
    return buf.value or None


OFN_OVERWRITEPROMPT = 0x00000002


def browse_for_save(title: str = "Save as", filter_spec: str = "",
                    initial_dir: str = "", default_name: str = "",
                    default_ext: str = "") -> Optional[str]:
    """Blocking native Save-As dialog. Returns the chosen path or None.

    The counterpart to :func:`browse_for_file`: exporting a unit pack has to end
    up somewhere the user picked, and a browser download would hand back a name
    with no path — which is no use to a server that has to write the file itself.
    Windows does the overwrite prompt for us (``OFN_OVERWRITEPROMPT``).
    """
    if sys.platform != "win32":
        return None
    spec = filter_spec or "All files (*.*)|*.*"
    filt = "\0".join(spec.split("|")) + "\0\0"
    buf = ctypes.create_unicode_buffer(2048)
    if default_name:
        buf.value = default_name
    ofn = _OPENFILENAMEW()
    ofn.lStructSize = ctypes.sizeof(_OPENFILENAMEW)
    ofn.lpstrFilter = filt
    ofn.lpstrFile = ctypes.cast(buf, wintypes.LPWSTR)
    ofn.nMaxFile = len(buf)
    ofn.lpstrTitle = title
    ofn.lpstrInitialDir = initial_dir or None
    ofn.lpstrDefExt = default_ext or None
    ofn.Flags = OFN_PATHMUSTEXIST | OFN_OVERWRITEPROMPT | OFN_EXPLORER
    comdlg32 = ctypes.windll.comdlg32
    comdlg32.GetSaveFileNameW.restype = wintypes.BOOL
    comdlg32.GetSaveFileNameW.argtypes = [ctypes.POINTER(_OPENFILENAMEW)]
    with _Owner() as owner:
        ofn.hwndOwner = owner
        if not comdlg32.GetSaveFileNameW(ctypes.byref(ofn)):
            return None
    return buf.value or None


def browse_for_folder(title: str = "Select a folder") -> Optional[str]:
    """Blocking native folder-picker. Returns the chosen path, or None if the
    user cancelled (or this isn't Windows)."""
    if sys.platform != "win32":
        return None
    ctypes.windll.ole32.CoInitialize(None)
    try:
        display_name = ctypes.create_unicode_buffer(260)
        bi = _BROWSEINFO()
        bi.pszDisplayName = ctypes.cast(display_name, wintypes.LPWSTR)
        bi.lpszTitle = title
        bi.ulFlags = BIF_RETURNONLYFSDIRS | BIF_NEWDIALOGSTYLE
        with _Owner() as owner:
            bi.hwndOwner = owner
            pidl = _shell32.SHBrowseForFolderW(ctypes.byref(bi))
        if not pidl:
            return None
        try:
            path_buf = ctypes.create_unicode_buffer(260)
            _shell32.SHGetPathFromIDListW(pidl, path_buf)
            return path_buf.value or None
        finally:
            _ole32.CoTaskMemFree(pidl)
    finally:
        ctypes.windll.ole32.CoUninitialize()


def reveal(path: str) -> bool:
    """Show ``path`` in the OS file manager, with the file itself selected.

    The same "the server IS this machine" trick as the dialogs above: a browser
    page cannot open a folder, but the process serving it can.

    Windows is the fussy one. ``explorer /select,<path>`` needs the comma glued
    to the switch and the path quoted *inside* the same argument, and passing a
    LIST does the opposite: :func:`subprocess.list2cmdline` wraps the whole
    ``/select,<a path with a space in it>`` token in quotes the moment the path
    has a space in it, Explorer fails to parse the switch, and it silently opens
    the user's Documents folder instead. Every real mod path has a space
    in it somewhere, so this passes one command STRING and quotes the path
    itself. ``normpath`` goes with it: Explorer will not follow forward slashes.

    Returns whether the file manager was launched. Explorer answers 1 even on
    success, so the exit code is not worth waiting for; anything that stops the
    process starting at all raises and comes back False.
    """
    import os
    import subprocess
    target = os.path.normpath(os.path.abspath(path))
    if not os.path.exists(target):
        return False
    try:
        if sys.platform == "win32":
            # one command string, path quoted inside the /select argument
            subprocess.Popen('explorer /select,"%s"' % target)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", "-R", target])
        else:
            # no portable "select the file" on Linux — open the folder it is in
            subprocess.Popen(["xdg-open", os.path.dirname(target)])
    except OSError:
        return False
    return True
