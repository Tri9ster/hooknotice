"""hooknotice の設定ファイル（config.json）の読み書き（標準ライブラリのみ）。

`hook_notify.py`（システムの python3）と `notify_window.py` / `settings_window.py`（venv の python3）から使う。
通知は1件ごとに新しいプロセスで起動するので、設定ファイルを書き換えれば次の通知から反映される。
ファイルが無い・壊れている・値が範囲外の場合は、例外を出さずに既定値を使う。
"""
from __future__ import annotations

import json
import math
import os
import tempfile
from dataclasses import dataclass, field

from platform_support import DEFAULT_SYSTEM_SOUND, plugin_data_dir, system_sound_path

# プラグインなら更新しても残る <DATA>/config.json、それ以外はこのファイルと同じフォルダ
CONFIG_PATH = os.path.join(plugin_data_dir() or os.path.dirname(os.path.abspath(__file__)), "config.json")

DEFAULT_WIDTH = 600
WIDTH_RANGE = (280, 800)
LINE_LIMIT_RANGE = (20, 200)
DEFAULT_DELAY_SECONDS = 6  # 通知を出すまでの待ち時間（Claude Code の permission_prompt と同じ約6秒）
DELAY_RANGE = (0, 60)
# 待ち時間の決め方: fixed（delay_seconds のまま）/ reading（本文の文字数から。delay_seconds は最低の待ち時間）
DELAY_MODES = ("fixed", "reading")
DEFAULT_READING_CPM = 600  # 1分あたりに読む文字数
READING_CPM_RANGE = (100, 3000)
READING_DELAY_MAX = 120  # 文字数から決めるときの上限（秒）
# 表示の言語: auto（OS の言語が日本語なら ja、それ以外は en）/ ja / en。文言は messages.py
LANGUAGES = ("auto", "ja", "en")
# 解説（claude -p）のモデルと effort。設定画面は無く、config.json の explain で変える
DEFAULT_EXPLAIN_MODEL = "sonnet"
EXPLAIN_EFFORTS = ("low", "medium", "high", "xhigh", "max")
DEFAULT_EXPLAIN_EFFORT = "low"

# コマンド欄の1文字の幅（Menlo 11px の実測値）と、カード幅のうち文字に使えない分
# （左右の余白 12+8、枠と padding 8、スクロールバー 6）
COMMAND_CHAR_WIDTH_PX = 6.61
COMMAND_NON_TEXT_PX = 34


@dataclass(frozen=True)
class Scene:
    """通知する場面。key は config.json の notify のキー（Notification は notification_type と同じ名前）。

    表示名と説明は messages.py の scene.<key>.label / scene.<key>.desc、分類の見出しは group.<group>。
    """

    key: str
    default: bool
    group: str  # 設定画面での分類のキー


# 設定画面にはこの順に並べる。既定オフは、ほかの通知と重複するものと、報告だけのもの
SCENES = (
    Scene("permission_request", True, "answer"),
    Scene("question", True, "answer"),
    Scene("plan", True, "answer"),
    Scene("permission_prompt", False, "answer"),  # 「許可待ち」と重複するため既定オフ
    Scene("stop", True, "milestone"),
    Scene("stop_failure", True, "milestone"),
    Scene("idle_prompt", False, "milestone"),  # 「作業完了」と重複するため既定オフ
    Scene("elicitation_dialog", True, "mcp"),
    Scene("elicitation_url_dialog", True, "mcp"),
    Scene("elicitation_complete", False, "mcp"),
    Scene("elicitation_response", False, "mcp"),
    Scene("agent_needs_input", True, "background"),
    Scene("agent_completed", True, "background"),
    Scene("quota_auto_resume_fired", True, "quota"),
    Scene("quota_auto_resume_stale", True, "quota"),
    Scene("quota_auto_resume_disabled", True, "quota"),
    Scene("subagent_stop", False, "agent"),  # 頻繁に出るため既定オフ
    Scene("task_completed", False, "agent"),
    Scene("teammate_idle", False, "agent"),
    Scene("auth_success", False, "other"),
)
NOTIFY_DEFAULTS = {scene.key: scene.default for scene in SCENES}


@dataclass(frozen=True)
class Config:
    width: int  # 通知カードの横幅（px）
    command_line_limit: int  # 長いコマンドを改行する文字数
    notify: dict = field(default_factory=lambda: dict(NOTIFY_DEFAULTS))  # 場面ごとのオン/オフ
    delay_seconds: int = DEFAULT_DELAY_SECONDS  # この秒数放置されたら通知を出す（0 ですぐ）
    delay_mode: str = "fixed"  # DELAY_MODES のどれか
    reading_cpm: int = DEFAULT_READING_CPM  # delay_mode が reading のときの、1分あたりに読む文字数
    sound_enabled: bool = True  # 通知音を鳴らすか
    sound_source: str = "system"  # "system"（システムの通知音）/ "file"（任意の音声ファイル）
    sound_system: str = DEFAULT_SYSTEM_SOUND  # システムの通知音の名前（拡張子なし）
    sound_file: str = ""  # 任意の音声ファイルのパス
    suppress_when_focused: bool = False  # Claude Code を起動したアプリが最前面のときは通知しない（macOS）
    language: str = "auto"  # LANGUAGES のどれか
    explain_model: str = DEFAULT_EXPLAIN_MODEL  # 解説に使うモデル（claude --model に渡す文字列）
    explain_effort: str = DEFAULT_EXPLAIN_EFFORT  # EXPLAIN_EFFORTS のどれか

    def sound_path(self) -> str:
        """鳴らす音声ファイルのパス。鳴らさないなら空文字。任意のファイルが無くなっていればシステムの音にする。"""
        if not self.sound_enabled:
            return ""
        if self.sound_source == "file" and self.sound_file and os.path.isfile(self.sound_file):
            return self.sound_file
        return system_sound_path(self.sound_system)

    def delay_for(self, char_count: int) -> int:
        """本文が char_count 文字の通知を出すまでの待ち時間（秒）。0 ならすぐ出す。"""
        if self.delay_mode != "reading" or not self.delay_seconds:
            return self.delay_seconds
        reading = math.ceil(char_count * 60 / self.reading_cpm)
        return max(self.delay_seconds, min(reading, READING_DELAY_MAX))

    def enabled(self, key: str) -> bool:
        """その場面で通知するか。一覧に無い（将来増えた）場面は通知する。"""
        return self.notify.get(key, True)


def auto_line_limit(width: int) -> int:
    """カード幅から、コマンド欄で折り返さずに収まる文字数（少し余裕を残す）を求める。340px → 44、600px → 83。"""
    return int((width - COMMAND_NON_TEXT_PX) // COMMAND_CHAR_WIDTH_PX) - 2


def _int_in_range(value, value_range: tuple[int, int]) -> int | None:
    # bool は int の一種なので除く（true を 1 と解釈しない）
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    low, high = value_range
    return value if low <= value <= high else None


def _read_json(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def load_config(path: str = CONFIG_PATH) -> Config:
    data = _read_json(path)

    width = _int_in_range(data.get("width"), WIDTH_RANGE) or DEFAULT_WIDTH
    line_limit = _int_in_range(data.get("command_line_limit"), LINE_LIMIT_RANGE)
    if line_limit is None:  # null・未指定・不正な値は幅から自動計算
        line_limit = auto_line_limit(width)
    notify = dict(NOTIFY_DEFAULTS)
    raw_notify = data.get("notify")
    if isinstance(raw_notify, dict):
        notify.update({k: v for k, v in raw_notify.items() if isinstance(k, str) and isinstance(v, bool)})
    sound = data.get("sound") if isinstance(data.get("sound"), dict) else {}
    explain = data.get("explain") if isinstance(data.get("explain"), dict) else {}
    model = explain.get("model")
    return Config(
        width=width,
        command_line_limit=line_limit,
        notify=notify,
        delay_seconds=_int_in_range(data.get("delay_seconds"), DELAY_RANGE)
        if _int_in_range(data.get("delay_seconds"), DELAY_RANGE) is not None else DEFAULT_DELAY_SECONDS,
        delay_mode=data.get("delay_mode") if data.get("delay_mode") in DELAY_MODES else "fixed",
        reading_cpm=_int_in_range(data.get("reading_cpm"), READING_CPM_RANGE) or DEFAULT_READING_CPM,
        sound_enabled=sound.get("enabled") if isinstance(sound.get("enabled"), bool) else True,
        sound_source="file" if sound.get("source") == "file" else "system",
        sound_system=sound.get("system") if isinstance(sound.get("system"), str) and sound.get("system")
        else DEFAULT_SYSTEM_SOUND,
        sound_file=sound.get("file") if isinstance(sound.get("file"), str) else "",
        suppress_when_focused=data.get("suppress_when_focused") if isinstance(data.get("suppress_when_focused"), bool)
        else False,
        language=data.get("language") if data.get("language") in LANGUAGES else "auto",
        explain_model=model.strip() if isinstance(model, str) and model.strip() else DEFAULT_EXPLAIN_MODEL,
        explain_effort=explain.get("effort") if explain.get("effort") in EXPLAIN_EFFORTS else DEFAULT_EXPLAIN_EFFORT,
    )


def save_config(values: dict, path: str = CONFIG_PATH) -> None:
    """values のキーだけを上書きして保存する（notify は場面ごとにマージ）。知らないキーはそのまま残す。

    書きかけのファイルを通知が読まないよう、一時ファイルに書いてから置き換える。
    """
    data = _read_json(path)
    for key, value in values.items():
        if key in ("notify", "sound") and isinstance(value, dict):
            merged = data.get(key) if isinstance(data.get(key), dict) else {}
            merged.update(value)
            data[key] = merged
        else:
            data[key] = value
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)  # プラグインの DATA はまだ無いことがある
    fd, tmp = tempfile.mkstemp(prefix=".config-", suffix=".json", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
