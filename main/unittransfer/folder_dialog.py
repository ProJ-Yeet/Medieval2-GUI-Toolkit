"""Native Windows folder-picker dialog for the Settings "Browse..." button.

The UI is a browser page, and browsers deliberately never expose a real
filesystem path from an `<input type="file">` picker. But the server IS this
machine, so it can pop the OS's own folder dialog (the Explorer-style
`IFileOpenDialog` the file pickers show, `SHBrowseForFolderW` only if COM
will not make one) and
hand the chosen path back over the API - the same trick a desktop app would
use, just triggered over HTTP instead of a local button handler.

ctypes + shell32 only (no tkinter): the portable build's embeddable Python
doesn't carry Tcl/Tk, but ctypes is always part of the stdlib.
"""
from __future__ import annotations

import ctypes
import os
import subprocess
import sys
import threading
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
# machines, as nothing but a flashing taskbar button - which reads exactly like
# "Browse... is stuck loading".
#
# The fix is to give the dialog an OWNER: a 1x1, fully transparent popup this
# process does own. Two properties of ownership do the work. An owned window is
# always drawn above its owner, and a WS_EX_TOPMOST owner passes topmost on to
# it - so the dialog cannot end up behind the browser whatever the foreground
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
# The owner has to be VISIBLE. `SetForegroundWindow` refuses a hidden or
# zero-size window, so a 0x0 never-shown popup could never take the foreground -
# which is how the dialog ended up behind the browser with nothing but a
# flashing taskbar button, reading as "Replace image... does nothing". A 1x1
# layered window at full transparency is visible to the window manager and
# invisible to the eye, so it satisfies the API without ever being seen.
WS_VISIBLE = 0x10000000
WS_EX_TOPMOST = 0x00000008
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_LAYERED = 0x00080000
LWA_ALPHA = 0x00000002
HWND_TOPMOST = -1
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_NOACTIVATE = 0x0010

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
_user32.SetLayeredWindowAttributes.argtypes = [
    wintypes.HWND, wintypes.COLORREF, ctypes.c_ubyte, wintypes.DWORD]
_user32.GetLastActivePopup.restype = wintypes.HWND
_user32.GetLastActivePopup.argtypes = [wintypes.HWND]
_user32.SetWindowPos.argtypes = [
    wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
    ctypes.c_int, ctypes.c_int, wintypes.UINT]
_user32.IsWindowVisible.argtypes = [wintypes.HWND]


class _Owner:
    """A hidden top-level window to hang a modal dialog off, as a context manager.

    ``with _Owner() as hwnd:`` - ``hwnd`` may be ``None`` (window creation is not
    worth failing a Browse over), and every dialog below already accepts a null
    owner, which is what it always used to pass.
    """

    def __enter__(self):
        self.hwnd = None
        self._stop = threading.Event()
        try:
            # "STATIC" is a class the system has already registered, so there is
            # no window class of our own to register, name-clash or clean up.
            # WS_VISIBLE and a 1x1 size are what make it eligible for the
            # foreground at all; WS_EX_LAYERED at alpha 0 is what stops anyone
            # seeing the pixel it occupies.
            self.hwnd = _user32.CreateWindowExW(
                WS_EX_TOPMOST | WS_EX_TOOLWINDOW | WS_EX_LAYERED,
                "STATIC", "", WS_POPUP | WS_VISIBLE,
                0, 0, 1, 1, None, None, None, None)
        except OSError:
            self.hwnd = None
        if self.hwnd:
            try:
                _user32.SetLayeredWindowAttributes(self.hwnd, 0, 0, LWA_ALPHA)
            except OSError:
                pass
            _force_foreground(self.hwnd)
            # …and once the dialog is up, put it in front on its own account.
            # Ownership alone only guarantees it sits above THIS window, and the
            # foreground lock can still refuse us at the moment the owner is
            # made; the dialog is a second chance at the same thing, taken from
            # a thread because the call that opens it does not return until the
            # user has answered.
            self._watch = threading.Thread(target=self._raise_dialog, daemon=True)
            self._watch.start()
        return self.hwnd

    def _raise_dialog(self) -> None:
        """Poll for the dialog this owner is about to get, and raise it."""
        for _ in range(60):                       # ~3s, then give up quietly
            if self._stop.wait(0.05):
                return
            try:
                dlg = _user32.GetLastActivePopup(self.hwnd)
                if dlg and dlg != self.hwnd and _user32.IsWindowVisible(dlg):
                    _user32.SetWindowPos(dlg, HWND_TOPMOST, 0, 0, 0, 0,
                                         SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)
                    _force_foreground(dlg)
                    return
            except OSError:
                return

    def __exit__(self, *exc):
        self._stop.set()
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
    ``"Meshes (*.mesh)|*.mesh|All files (*.*)|*.*"`` - the editor needs a real
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
    with no path - which is no use to a server that has to write the file itself.
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


# The folder picker is the same Explorer window the file dialogs open
# (IFileOpenDialog with FOS_PICKFOLDERS), not SHBrowseForFolderW's old tree
# box. It is a COM object, called through its vtable: ctypes has no COM of its
# own, and comtypes is not in the portable build.
class _GUID(ctypes.Structure):
    _fields_ = [("d1", wintypes.DWORD), ("d2", wintypes.WORD), ("d3", wintypes.WORD), ("d4", ctypes.c_ubyte * 8)]

    def __init__(self, text: str):
        super().__init__()
        _ole32.CLSIDFromString(text, ctypes.byref(self))


_ole32.CLSIDFromString.argtypes = [wintypes.LPCWSTR, ctypes.c_void_p]
_ole32.CoCreateInstance.argtypes = [ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD,
                                    ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
_CLSID_FILE_OPEN_DIALOG = "{DC1C5A9C-E88A-4DDE-A5A1-60F82A20AEF7}"
_IID_IFILE_OPEN_DIALOG = "{D57C7288-D4AD-4768-BE02-9D969532D960}"
FOS_PICKFOLDERS = 0x20
FOS_FORCEFILESYSTEM = 0x40
FOS_PATHMUSTEXIST = 0x800
SIGDN_FILESYSPATH = 0x80058000
_CANCELLED = 0x800704C7 - (1 << 32)        # HRESULT_FROM_WIN32(ERROR_CANCELLED)


def _vcall(obj, index: int, restype, *args):
    """Calls method ``index`` of a COM object's vtable."""
    argtypes = [ctypes.c_void_p] + [type(a) if isinstance(a, ctypes._SimpleCData) else ctypes.c_void_p for a in args]
    fn = ctypes.WINFUNCTYPE(restype, *argtypes)(ctypes.cast(obj, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p)))[0][index])
    return fn(obj, *args)


class _NoModernDialog(Exception):
    pass


def _pick_folder_modern(title: str, initial_dir: str = "") -> Optional[str]:
    """The Explorer-style folder picker; raises :class:`_NoModernDialog` if
    COM will not make one, so the old box can stand in."""
    dlg = ctypes.c_void_p()
    hr = _ole32.CoCreateInstance(ctypes.byref(_GUID(_CLSID_FILE_OPEN_DIALOG)), None, 1,
                                 ctypes.byref(_GUID(_IID_IFILE_OPEN_DIALOG)), ctypes.byref(dlg))
    if hr != 0 or not dlg:
        raise _NoModernDialog(hr)
    try:
        opts = wintypes.DWORD()
        _vcall(dlg, 10, ctypes.HRESULT, ctypes.byref(opts))                       # GetOptions
        _vcall(dlg, 9, ctypes.HRESULT,                                             # SetOptions
               wintypes.DWORD(opts.value | FOS_PICKFOLDERS | FOS_FORCEFILESYSTEM | FOS_PATHMUSTEXIST))
        _vcall(dlg, 17, ctypes.HRESULT, wintypes.LPCWSTR(title))                   # SetTitle
        if initial_dir and os.path.isdir(initial_dir):
            item = ctypes.c_void_p()
            iid = _GUID("{43826D1E-E718-42EE-BC55-A1E261C37BFE}")  # IShellItem
            create = _shell32.SHCreateItemFromParsingName
            create.argtypes = [wintypes.LPCWSTR, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
            create.restype = ctypes.HRESULT
            if create(initial_dir, None, ctypes.byref(iid), ctypes.byref(item)) == 0:
                try:
                    _vcall(dlg, 12, ctypes.HRESULT, item)  # SetFolder
                finally:
                    _vcall(item, 2, ctypes.c_ulong)
        with _Owner() as owner:
            hr = _vcall(dlg, 3, ctypes.c_long, wintypes.HWND(owner or 0))          # Show
        if hr == _CANCELLED:
            return None
        if hr != 0:
            raise _NoModernDialog(hr)
        item = ctypes.c_void_p()
        _vcall(dlg, 20, ctypes.HRESULT, ctypes.byref(item))                        # GetResult
        try:
            name = ctypes.c_wchar_p()
            _vcall(item, 5, ctypes.HRESULT, ctypes.c_ulong(SIGDN_FILESYSPATH), ctypes.byref(name))  # GetDisplayName
            try:
                return name.value or None
            finally:
                _ole32.CoTaskMemFree(ctypes.cast(name, ctypes.c_void_p))
        finally:
            _vcall(item, 2, ctypes.c_ulong)                                        # Release
    finally:
        _vcall(dlg, 2, ctypes.c_ulong)                                             # Release


def browse_for_folder(title: str = "Select a folder", initial_dir: str = "") -> Optional[str]:
    """Blocking native folder-picker. Returns the chosen path, or None if the
    user cancelled (or this isn't Windows)."""
    if sys.platform != "win32":
        return None
    ctypes.windll.ole32.CoInitialize(None)
    try:
        try:
            return _pick_folder_modern(title, initial_dir)
        except (_NoModernDialog, OSError):
            pass
        display_name = ctypes.create_unicode_buffer(260)
        bi = _BROWSEINFO()
        bi.pszDisplayName = ctypes.cast(display_name, wintypes.LPWSTR)
        bi.lpszTitle = title
        bi.ulFlags = BIF_RETURNONLYFSDIRS | BIF_NEWDIALOGSTYLE
        callback = None
        if initial_dir and os.path.isdir(initial_dir):
            def set_initial(hwnd, msg, _lp, _data):
                if msg == 1:  # BFFM_INITIALIZED
                    send = ctypes.windll.user32.SendMessageW
                    send.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
                    send(hwnd, 0x467, 1, ctypes.cast(ctypes.c_wchar_p(initial_dir), ctypes.c_void_p).value)
                return 0
            callback = ctypes.WINFUNCTYPE(ctypes.c_int, wintypes.HWND, wintypes.UINT,
                                         wintypes.LPARAM, wintypes.LPARAM)(set_initial)
            bi.lpfn = ctypes.cast(callback, ctypes.c_void_p)
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
            # no portable "select the file" on Linux - open the folder it is in
            subprocess.Popen(["xdg-open", os.path.dirname(target)])
    except OSError:
        return False
    return True


#: Editors that can be told which line to open at, by executable name, and how.
#: The OS association picks the editor; this only adds the line when the editor
#: it picked is one that takes one. Notepad takes none, and gets the file alone.
_LINE_ARGS = {
    "code": lambda p, n: ["-g", f"{p}:{n}"],
    "code - insiders": lambda p, n: ["-g", f"{p}:{n}"],
    "cursor": lambda p, n: ["-g", f"{p}:{n}"],
    "codium": lambda p, n: ["-g", f"{p}:{n}"],
    "vscodium": lambda p, n: ["-g", f"{p}:{n}"],
    "windsurf": lambda p, n: ["-g", f"{p}:{n}"],
    "notepad++": lambda p, n: [f"-n{n}", p],
    "sublime_text": lambda p, n: [f"{p}:{n}"],
    "subl": lambda p, n: [f"{p}:{n}"],
    "zed": lambda p, n: [f"{p}:{n}"],
    "atom": lambda p, n: [f"{p}:{n}"],
    "notepad2": lambda p, n: ["/g", str(n), p],
    "notepad3": lambda p, n: ["/g", str(n), p],
    "emeditor": lambda p, n: ["/l", str(n), p],
    "gvim": lambda p, n: [f"+{n}", p],
    "kate": lambda p, n: ["-l", str(n), p],
    "gedit": lambda p, n: [f"+{n}", p],
}


def _assoc_exe(ext: str) -> str:
    """The executable Windows opens ``ext`` files with, or '' when it has none."""
    import ctypes
    from ctypes import wintypes
    try:
        fn = ctypes.windll.shlwapi.AssocQueryStringW
    except (AttributeError, OSError):
        return ""
    fn.argtypes = [ctypes.c_uint, ctypes.c_uint, wintypes.LPCWSTR, wintypes.LPCWSTR,
                   wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
    size = wintypes.DWORD(1024)
    buf = ctypes.create_unicode_buffer(size.value)
    # ASSOCF_INIT_IGNOREUNKNOWN (0x400): no "pick an app" answer for an unknown
    # type; ASSOCSTR_EXECUTABLE (2)
    if fn(0x400, 2, ext, "open", buf, ctypes.byref(size)) != 0:
        return ""
    exe = buf.value
    # the "how do you want to open this?" stub is not an editor
    if not exe or os.path.basename(exe).lower() in ("openwith.exe", "rundll32.exe"):
        return ""
    return exe


def open_at_line(path: str, line: int = 0) -> dict:
    """Open ``path`` in the OS's own editor for it, at ``line`` when it can.

    The editor is whatever the OS opens that file type with - for a ``.lua``
    with nothing set, whatever opens a ``.txt`` - so it is the user's choice,
    never ours. Whether the line was honoured depends on that editor; the answer
    says so (``line``), and the page tells the user to go to it by hand when not.
    """
    target = os.path.normpath(os.path.abspath(path))
    if not os.path.isfile(target):
        return {"ok": False, "line": False}
    line = max(0, int(line or 0))
    try:
        if sys.platform == "win32":
            ext = os.path.splitext(target)[1] or ".txt"
            exe = _assoc_exe(ext) or _assoc_exe(".txt")
            if not exe:
                os.startfile(target)                     # noqa: S606
                return {"ok": True, "line": False}
            key = os.path.splitext(os.path.basename(exe))[0].lower()
            how = _LINE_ARGS.get(key)
            subprocess.Popen([exe] + (how(target, line) if how and line else [target]))
            return {"ok": True, "line": bool(how and line), "editor": key}
        if sys.platform == "darwin":
            subprocess.Popen(["open", "-t", target])
            return {"ok": True, "line": False}
        subprocess.Popen(["xdg-open", target])
        return {"ok": True, "line": False}
    except OSError:
        return {"ok": False, "line": False}
