"""OS ごとに異なる処理をまとめる（標準ライブラリのみ）。

`hook_notify.py`（システムの python3）と `notify_window.py`（venv の python3）の両方から使う。
macOS の処理は従来のまま。Windows の分岐は実機での確認がまだ（README の注記を参照）。
"""
from __future__ import annotations

import contextlib
import os
import plistlib
import shutil
import subprocess
import sys
from pathlib import Path

IS_WINDOWS = sys.platform == "win32"
IS_MAC = sys.platform == "darwin"
SUPPORTED = IS_MAC or IS_WINDOWS

ACTIVATE_SCRIPT = 'on run argv\n  tell application id (item 1 of argv) to activate\nend run'

# Windows API の定数（ctypes / subprocess 用）
_PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
_STILL_ACTIVE = 259
_CREATE_NEW_PROCESS_GROUP = 0x00000200
_CREATE_NO_WINDOW = 0x08000000
_LANG_JAPANESE = 0x11  # LANGID の主言語


def use_utf8_stdio() -> None:
    """Windows では標準入出力の既定が ANSI コードページ（cp932 等）なので UTF-8 にそろえる。"""
    if not IS_WINDOWS:
        return
    for stream in (sys.stdin, sys.stdout):
        if stream is not None and hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")


def system_language() -> str:
    """OS の表示言語が日本語なら "ja"、それ以外（判定できない場合を含む）は "en" を返す。

    macOS は「優先する言語」の先頭（AppleLanguages）を、サブプロセスを使わずに設定ファイルから読む。
    Windows は UI の言語。どちらも取れなければ環境変数 LC_ALL / LC_MESSAGES / LANG を見る。
    """
    code = ""
    if IS_MAC:
        try:
            with open(Path.home() / "Library" / "Preferences" / ".GlobalPreferences.plist", "rb") as f:
                languages = plistlib.load(f).get("AppleLanguages")
            if isinstance(languages, list) and languages and isinstance(languages[0], str):
                code = languages[0]
        except (OSError, ValueError, plistlib.InvalidFileException):
            pass
    elif IS_WINDOWS:
        try:
            import ctypes

            if ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0x3FF == _LANG_JAPANESE:
                return "ja"
            return "en"
        except (OSError, AttributeError):
            pass
    if not code:
        for name in ("LC_ALL", "LC_MESSAGES", "LANG"):
            code = os.environ.get(name, "")
            if code:
                break
    return "ja" if code.lower().startswith("ja") else "en"


def plugin_data_dir() -> str:
    """プラグインとして動いているときの、更新しても残るデータの置き場所（CLAUDE_PLUGIN_DATA）。

    Claude Code が Hook のプロセスに渡し、そこから起動する notify_window.py / settings_window.py にも引き継がれる。
    プラグインの本体（CLAUDE_PLUGIN_ROOT）は更新のたびに入れ替わるので、venv と設定はこちらに置く。
    プラグインでなく手で置いて動かしているときは空文字。
    """
    return os.environ.get("CLAUDE_PLUGIN_DATA", "")


def venv_dir(hooknotice_dir: str) -> str:
    """notify_window.py を動かす venv。プラグインなら <DATA>/venv、それ以外は hooknotice_dir/.venv。"""
    data = plugin_data_dir()
    return os.path.join(data, "venv") if data else os.path.join(hooknotice_dir, ".venv")


def venv_python(hooknotice_dir: str) -> str:
    """notify_window.py を動かす venv の Python。

    Windows は pythonw ではなく python.exe を使い、コンソール窓は CREATE_NO_WINDOW で出さない
    （回答を stdout で確実に受け取るため）。
    """
    if IS_WINDOWS:
        return os.path.join(venv_dir(hooknotice_dir), "Scripts", "python.exe")
    return os.path.join(venv_dir(hooknotice_dir), "bin", "python3")


def popen_flags(detach: bool) -> dict:
    """subprocess に渡す起動オプション。detach は Hook の終了後も通知を残す（切り離して起動する）とき。"""
    if IS_WINDOWS:
        flags = _CREATE_NO_WINDOW | (_CREATE_NEW_PROCESS_GROUP if detach else 0)
        return {"creationflags": flags}
    return {"start_new_session": True} if detach else {}


def bash_path() -> str:
    """コマンド整形の構文チェックに使う bash。Windows は Git Bash を探し、無ければ空文字。"""
    if IS_WINDOWS:
        return shutil.which("bash") or ""
    return "/bin/bash"


def state_dir() -> Path:
    """表示中の通知一覧（stack_state.json）を置くディレクトリ。"""
    if IS_WINDOWS:
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / "hooknotice"
    return Path.home() / "Library" / "Application Support" / "hooknotice"


@contextlib.contextmanager
def locked_state(path: Path):
    """状態ファイルを排他ロックして r+ で開き、ファイルオブジェクトを渡す。

    Windows のバイト範囲ロックは強制ロックで、ロックした範囲は他のプロセスから読めなくなるため、
    状態ファイルとは別のロック用ファイルをロックする。
    """
    if not IS_WINDOWS:
        import fcntl

        with open(path, "r+", encoding="utf-8") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            yield f
        return

    import msvcrt

    lock_path = path.with_suffix(".lock")
    with open(lock_path, "a+b") as lock:
        lock.seek(0)
        msvcrt.locking(lock.fileno(), msvcrt.LK_LOCK, 1)  # 取れるまで約10秒待ち、だめなら OSError
        try:
            with open(path, "r+", encoding="utf-8") as f:
                yield f
        finally:
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)


def try_lock(path: Path):
    """排他ロックを待たずに取る。取れたら開いたファイル（閉じると解放）を、他が持っていれば None を返す。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    f = open(path, "a+b")
    try:
        if IS_WINDOWS:
            import msvcrt

            f.seek(0)
            msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        f.close()
        return None
    return f


def find_uv() -> str:
    """uv の実行ファイル。Hook の PATH は短いことがあるので、よくある置き場所も探す。見つからなければ空文字。

    環境変数 HOOKNOTICE_UV があれば、そのパスだけを使う（別の場所に入れた場合や、テスト用）。
    """
    override = os.environ.get("HOOKNOTICE_UV")
    if override is not None:
        return override if override and is_executable(override) else ""
    found = shutil.which("uv")
    if found:
        return found
    home = Path.home()
    if IS_WINDOWS:
        local = os.environ.get("LOCALAPPDATA") or str(home / "AppData" / "Local")
        candidates = [
            home / ".local" / "bin" / "uv.exe",
            home / ".cargo" / "bin" / "uv.exe",
            Path(local) / "Microsoft" / "WinGet" / "Links" / "uv.exe",
        ]
    else:
        candidates = [
            home / ".local" / "bin" / "uv",
            Path("/opt/homebrew/bin/uv"),
            Path("/usr/local/bin/uv"),
            home / ".cargo" / "bin" / "uv",
        ]
    for path in candidates:
        if is_executable(str(path)):
            return str(path)
    return ""


def pid_alive(pid: int) -> bool:
    """プロセスが生きているか。Windows の os.kill(pid, 0) はプロセスを終了させてしまうので使わない。"""
    if pid == os.getpid():
        return True
    if not isinstance(pid, int) or pid <= 0:
        return False
    if IS_WINDOWS:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(_PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            return False
        try:
            code = ctypes.c_ulong()
            if not kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
                return False
            return code.value == _STILL_ACTIVE
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def parent_exited(parent_pid: int) -> bool:
    """起動元（回答を待つ Hook）が終了したか。

    macOS は親が終了すると親 pid が変わる（起動前に終了していれば launchd の pid 1 になる）。
    Windows は親が終了しても親 pid が変わらないので、親 pid の生存を直接調べる。
    """
    if IS_WINDOWS:
        return not pid_alive(parent_pid)
    ppid = os.getppid()
    return ppid == 1 or ppid != parent_pid


# システムの通知音の既定（macOS は /System/Library/Sounds、Windows は %SystemRoot%\\Media の中の名前）
DEFAULT_SYSTEM_SOUND = "Windows Notify System Generic" if IS_WINDOWS else "Glass"
# 任意の音源として選べる形式（Windows の winsound は WAV しか鳴らせない）
SOUND_FILE_SUFFIXES = (".wav",) if IS_WINDOWS else (".aiff", ".aif", ".wav", ".mp3", ".m4a", ".caf")


def system_sound_dir() -> str:
    """システムの通知音が入っているフォルダ。"""
    if IS_WINDOWS:
        return os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "Media")
    return "/System/Library/Sounds"


def _system_sound_suffix() -> str:
    return ".wav" if IS_WINDOWS else ".aiff"


def list_system_sounds() -> list[str]:
    """選べるシステムの通知音の名前（拡張子なし）を名前順に返す。"""
    try:
        names = os.listdir(system_sound_dir())
    except OSError:
        return []
    suffix = _system_sound_suffix()
    return sorted(n[: -len(suffix)] for n in names if n.lower().endswith(suffix))


def system_sound_path(name: str) -> str:
    """システムの通知音の名前をファイルのパスにする。"""
    return os.path.join(system_sound_dir(), name + _system_sound_suffix())


def play_sound(path: str) -> None:
    """音声ファイルを鳴らす（待たない）。path が空なら無音。ファイルが無ければ鳴らさない。"""
    if not path or not os.path.isfile(path):
        return
    if IS_WINDOWS:
        import winsound

        try:
            winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
        except RuntimeError:
            pass  # WAV として再生できないファイル
        return
    subprocess.Popen(["afplay", path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


_DIALOG_SCRIPT = """on run argv
  set btns to items 4 thru -1 of argv
  activate
  if (item 3 of argv) is "0" then
    set r to display dialog (item 1 of argv) with title (item 2 of argv) buttons btns default button (last item of btns) with icon note
  else
    set r to display dialog (item 1 of argv) with title (item 2 of argv) buttons btns default button (last item of btns) with icon note giving up after ((item 3 of argv) as integer)
  end if
  return button returned of r
end run"""

# Windows の MessageBox の戻り値
_IDOK, _IDCANCEL, _IDYES, _IDNO = 1, 2, 6, 7


def ask_dialog(
    title: str, message: str, buttons: list[str], timeout: int = 0, button_hints: tuple[str, str] = ("", ""),
) -> str:
    """OS 標準のダイアログを出し、押されたボタンの名前を返す（1〜3個。最後のボタンが既定）。

    閉じられた・時間切れ（timeout 秒。0 は無制限）・表示できなかったときは空文字。
    Windows は MessageBox の OK / はい・いいえ・キャンセル に割り当て、対応を本文の末尾に書き添える。
    button_hints はその書き添えの書式（ボタン2個用, 3個用）。`{0}` から順にボタンの名前が入る（文言は呼び出し側が持つ）。
    """
    if IS_MAC:
        try:
            out = subprocess.run(
                ["osascript", "-e", _DIALOG_SCRIPT, message, title, str(timeout), *buttons],
                capture_output=True, text=True,
            ).stdout.strip()
        except OSError:
            return ""
        return out if out in buttons else ""
    if IS_WINDOWS:
        import ctypes

        if len(buttons) == 1:
            style, mapping = 0x0, {_IDOK: buttons[0]}  # MB_OK
        elif len(buttons) == 2:
            style, mapping = 0x1, {_IDOK: buttons[1], _IDCANCEL: buttons[0]}  # MB_OKCANCEL
            if button_hints[0]:
                message += "\n\n" + button_hints[0].format(*buttons)
        else:
            style = 0x3  # MB_YESNOCANCEL
            mapping = {_IDYES: buttons[2], _IDNO: buttons[1], _IDCANCEL: buttons[0]}
            if button_hints[1]:
                message += "\n\n" + button_hints[1].format(*buttons)
        style |= 0x40 | 0x10000 | 0x40000  # MB_ICONINFORMATION | MB_SETFOREGROUND | MB_TOPMOST
        result = ctypes.windll.user32.MessageBoxW(None, message, title, style)
        return mapping.get(result, "")
    return ""


def copy_to_clipboard(text: str) -> None:
    """文字列をクリップボードに入れる（macOS は pbcopy、Windows は clip）。"""
    command = ["clip"] if IS_WINDOWS else ["pbcopy"]
    encoding = "utf-16-le" if IS_WINDOWS else "utf-8"  # clip は UTF-16 を受け付ける
    try:
        subprocess.run(command, input=text.encode(encoding), **popen_flags(detach=False))
    except OSError:
        pass


def activate_app(bundle_id: str) -> None:
    """通知の発火元アプリを前面に出す。Windows は前面化の制限が強いため何もしない。"""
    if not IS_MAC or not bundle_id:
        return
    subprocess.Popen(
        ["osascript", "-e", ACTIVATE_SCRIPT, bundle_id],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def frontmost_app_id() -> str:
    """いま最前面（フォーカス中）のアプリの bundle id。macOS のみ。判定できなければ空文字。

    `lsappinfo` は LaunchServices に直接問い合わせるので、osascript と違って自動操作の許可が要らず速い。
    Windows は発火元アプリの識別子が無いため未対応（空文字）。
    """
    if not IS_MAC:
        return ""
    try:
        asn = subprocess.run(
            ["lsappinfo", "front"], capture_output=True, text=True, timeout=3,
        ).stdout.strip()
        if not asn:
            return ""
        out = subprocess.run(
            ["lsappinfo", "info", "-only", "bundleid", asn], capture_output=True, text=True, timeout=3,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return ""
    # 出力は `"CFBundleIdentifier"="com.apple.Terminal"`
    return out.partition("=")[2].strip().strip('"')


def is_executable(path: str) -> bool:
    """実行できるファイルか。Windows の os.access(X_OK) は常に真なので存在だけを見る。"""
    if IS_WINDOWS:
        return os.path.isfile(path)
    return os.access(path, os.X_OK)
