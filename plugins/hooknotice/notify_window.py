#!/usr/bin/env python3
"""通知ウィンドウ本体（PySide6。macOS・Windows。OS ごとの違いは platform_support.py）。

`hook_notify.py` から `uv` 管理の venv 経由で、通知1件につき使い捨てのプロセスとして
起動される。常駐デーモンやプロセス間IPCは持たない。複数の通知が同時に表示される際に
重ならないよう、`STATE_PATH` の小さなJSONファイルをファイルロックで排他制御して
スタック段（縦に並べる位置）と各通知の高さだけを共有する。
"""
from __future__ import annotations

import argparse
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile

from hooknotice_config import load_config
from messages import tr
from platform_support import (
    activate_app,
    is_executable,
    locked_state,
    parent_exited,
    pid_alive,
    play_sound,
    popen_flags,
    state_dir,
    use_utf8_stdio,
)
from PySide6.QtCore import (
    QEasingCurve,
    QPoint,
    QPointF,
    QProcess,
    QProcessEnvironment,
    QPropertyAnimation,
    QRect,
    QRectF,
    Qt,
    QEvent,
    QTimer,
)
from PySide6.QtGui import (
    QBrush,
    QColor,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QTextBlockFormat,
    QTextCharFormat,
    QTextCursor,
    QTextFormat,
    QTextOption,
)
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

CONFIG = load_config()
WIDTH = CONFIG.width  # config.json の width（既定 600）
HEIGHT = 110  # 最小の高さ。内容が多いときは画面に収まる範囲で縦に伸びる
MARGIN = 16
GAP = 10
CORNER_RADIUS = 12  # macOSの純正ダイアログ相当の角丸半径

# 「解説」ボタンで Claude に操作の解説を書かせる（claude -p を非同期で起動する）
EXPLAIN_MODEL = "sonnet"
EXPLAIN_MIN_HEIGHT = 80  # 画面に収まらないとき、解説欄はこの高さまで縮めてスクロールさせる
EXPLAIN_HEADING_PX = {1: 14, 2: 13, 3: 13}  # 見出しの文字サイズ（本文は 11px、4以下は 12px）
# 解説を頼むシステムプロンプトは messages.py の explain.prompt（言語ごと）

STACK_POLL_INTERVAL_MS = 250
MOVE_ANIMATION_MS = 200
CLICK_SHRINK_RATIO = 0.94
CLICK_ANIMATION_MS = 120

BASE_HUE_DEGREES = 220.0
HUE_JITTER_DEGREES = 20.0
POINT_JITTER_RATIO = 0.1
PHASE_STEP_RANGE = (0.008, 0.014)
ANIMATION_INTERVAL_MS = 40

# ハイライト帯の半幅（位相軸上の距離）。帯の中心がこの幅ぶん画面外(0未満・1超)を
# 通過し終えてから折り返すことで、出現・消失が画面端で唐突に途切れない。
BAND_WIDTH = 0.45
PHASE_RANGE_MIN = -BAND_WIDTH
PHASE_RANGE_MAX = 1.0 + BAND_WIDTH
GRADIENT_SAMPLE_POSITIONS = [i / 10 for i in range(11)]

# macOS の外観設定（ライト/ダーク）ごとの配色。色の組み合わせは STYLE_SHEET に差し込む。
THEMES = {
    "dark": {
        "base": "#2b2b2b",
        "highlight_saturation": (0.12, 0.18),
        "highlight_lightness": (0.30, 0.36),
        "border": None,
        "title": "#ffffff",
        "body": "#cccccc",
        "description": "#eeeeee",
        "command": "#dddddd",
        "command_bg": "rgba(0, 0, 0, 90)",
        "scrollbar": "rgba(255, 255, 255, 80)",
        "close": "#cccccc",
        "close_hover": "#ffffff",
        "action": "#cccccc",
        "action_bg": "rgba(255, 255, 255, 30)",
        "action_bg_hover": "rgba(255, 255, 255, 55)",
        "explain": "#dddddd",
        "explain_bg": "rgba(0, 0, 0, 60)",
        "code_bg": QColor(255, 255, 255, 22),  # 解説中のコード片の背景
    },
    "light": {
        "base": "#f2f2f4",
        "highlight_saturation": (0.25, 0.35),
        "highlight_lightness": (0.86, 0.92),
        "border": QColor(0, 0, 0, 40),  # 白いウィンドウの上で輪郭が溶けないように縁取る
        "title": "#1d1d1f",
        "body": "#555555",
        "description": "#333333",
        "command": "#222222",
        "command_bg": "rgba(0, 0, 0, 18)",
        "scrollbar": "rgba(0, 0, 0, 80)",
        "close": "#666666",
        "close_hover": "#000000",
        "action": "#333333",
        "action_bg": "rgba(0, 0, 0, 18)",
        "action_bg_hover": "rgba(0, 0, 0, 30)",
        "explain": "#222222",
        "explain_bg": "rgba(255, 255, 255, 150)",
        "code_bg": QColor(0, 0, 0, 14),
    },
}

STYLE_SHEET = """
    QLabel#title {{
        color: {title};
        font-weight: bold;
        font-size: 13px;
    }}
    QLabel#body {{
        color: {body};
        font-size: 11px;
    }}
    QLabel#description {{
        color: {description};
        font-size: 12px;
    }}
    QTextEdit#command {{
        color: {command};
        background: {command_bg};
        border: none;
        border-radius: 6px;
        padding: 4px;
        font-family: Menlo, Monaco, Consolas, monospace;
        font-size: 11px;
    }}
    QTextBrowser#explain, QTextBrowser#markdown {{
        color: {explain};
        background: {explain_bg};
        border: none;
        border-radius: 6px;
        padding: 4px;
        font-size: 11px;
    }}
    QScrollBar:vertical {{
        background: transparent;
        width: 6px;
    }}
    QScrollBar::handle:vertical {{
        background: {scrollbar};
        border-radius: 3px;
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}
    QPushButton {{
        color: {close};
        background: transparent;
        border: none;
        font-size: 14px;
    }}
    QPushButton:hover {{
        color: {close_hover};
    }}
    QPushButton#action {{
        color: {action};
        background: {action_bg};
        border-radius: 6px;
        font-size: 12px;
        padding: 4px 14px;
    }}
    QPushButton#action:hover {{
        background: {action_bg_hover};
    }}
    QPushButton#action:disabled {{
        color: {body};
    }}
    QPushButton#primary {{
        color: #ffffff;
        background: #2f6fde;
        border-radius: 6px;
        font-size: 12px;
        padding: 4px 14px;
    }}
    QPushButton#primary:hover {{
        background: #4a84ea;
    }}
    QPushButton#primary:disabled {{
        color: {action};
        background: {action_bg};
    }}
    QPushButton#choice {{
        color: {action};
        background: {action_bg};
        border-radius: 6px;
        font-size: 12px;
        padding: 4px 10px;
        text-align: left;
    }}
    QPushButton#choice:hover {{
        background: {action_bg_hover};
    }}
    QPushButton#choice:checked {{
        color: #ffffff;
        background: #2f6fde;
    }}
"""

STATE_DIR = state_dir()
STATE_PATH = STATE_DIR / "stack_state.json"

# --actions 指定時に stdout へ出力する結果（hook_notify.py と共通）
RESULT_ALLOW = "allow"
RESULT_DENY = "deny"
RESULT_DISMISS = "dismiss"  # ✕・本体クリック。決定せずターミナルに委ねる
# --plan-actions（計画の承認待ち）のボタン。承認は切り替え先の権限モードごとに分ける
RESULT_PLAN_AUTO = "plan_auto"
RESULT_PLAN_ACCEPT_EDITS = "plan_accept_edits"
RESULT_PLAN_DEFAULT = "plan_default"
# --questions（選択肢の質問）で回答したときの結果の接頭辞。後ろに {質問文: 選んだ選択肢} の JSON が続く
RESULT_ANSWERS_PREFIX = "answers "
PLAN_BUTTONS = (  # 2列のグリッドに左上から並べる（文言のキー, objectName, 結果）
    ("button.plan_continue", "action", RESULT_DENY),
    ("button.plan_default", "action", RESULT_PLAN_DEFAULT),
    ("button.plan_accept_edits", "action", RESULT_PLAN_ACCEPT_EDITS),
    ("button.plan_auto", "primary", RESULT_PLAN_AUTO),
)

def _smoothstep(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def _lerp_color(base: QColor, highlight: QColor, t: float) -> QColor:
    t = max(0.0, min(1.0, t))
    r = base.red() + (highlight.red() - base.red()) * t
    g = base.green() + (highlight.green() - base.green()) * t
    b = base.blue() + (highlight.blue() - base.blue()) * t
    return QColor(int(r), int(g), int(b))


def _current_theme() -> str:
    """システムの外観設定に対応するテーマ名を返す。判定できなければ従来どおりダーク。"""
    scheme = QApplication.styleHints().colorScheme()
    return "light" if scheme == Qt.ColorScheme.Light else "dark"


class StackSlot:
    """常駐デーモンなしで複数プロセス間のスタック順を共有する。

    状態ファイルは表示中の通知を到着順に並べたリスト（各要素は pid と高さ）で、
    新しい通知ほど下の段になる。通知ごとに高さが違うため、各プロセスは定期的に
    自分より新しい通知の高さを読み直し、新しい通知が来たら上へずれ、下の通知が閉じられたら下に詰める。
    異常終了したプロセスの記録は pid の生存確認で回収する。
    """

    def __init__(self) -> None:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        STATE_PATH.touch(exist_ok=True)

    def acquire(self, height: int) -> None:
        with locked_state(STATE_PATH) as f:
            entries = [e for e in self._read(f) if pid_alive(e.get("pid", -1))]
            entries.append({"pid": os.getpid(), "height": height})
            self._write(f, entries)

    def heights_newest_to_self(self) -> list[int] | None:
        """最新の通知から自分までの、表示中の通知の高さのリストを返す（先頭が最新、末尾が自分）。"""
        try:
            with locked_state(STATE_PATH) as f:
                entries = self._read(f)
                alive = [e for e in entries if pid_alive(e.get("pid", -1))]
                if len(alive) != len(entries):
                    self._write(f, alive)
        except OSError:
            return None
        pids = [e.get("pid") for e in alive]
        if os.getpid() not in pids:
            return None
        # 高さを記録していない旧形式のエントリは最小の高さとみなす
        return [e.get("height", HEIGHT) for e in reversed(alive[pids.index(os.getpid()) :])]

    def update_height(self, height: int) -> None:
        """表示中に高さが変わった（解説を表示した）ときに記録を書き換える。上の通知はポーリングで追従する。"""
        try:
            with locked_state(STATE_PATH) as f:
                entries = self._read(f)
                for entry in entries:
                    if entry.get("pid") == os.getpid():
                        entry["height"] = height
                self._write(f, entries)
        except OSError:
            pass

    def release(self) -> None:
        try:
            with locked_state(STATE_PATH) as f:
                entries = [e for e in self._read(f) if e.get("pid") != os.getpid()]
                self._write(f, entries)
        except OSError:
            pass

    @staticmethod
    def _read(f) -> list:
        f.seek(0)
        raw = f.read().strip()
        if not raw:
            return []
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return []
        return data if isinstance(data, list) else []

    @staticmethod
    def _write(f, entries: list) -> None:
        f.seek(0)
        f.truncate()
        f.write(json.dumps(entries))
        f.flush()


def _stack_position(heights: list[int], geometry) -> tuple[int, int]:
    """最新の通知から自分までの高さを下から順に積み、自分（末尾）の表示位置を計算する。

    画面の上端を超える場合は、1列左の列に折り返して積み直す。
    """
    top = geometry.top() + MARGIN
    bottom = geometry.bottom() - MARGIN
    column, y = 0, bottom - heights[0]
    for i, height in enumerate(heights):
        if i > 0:
            y -= height + GAP
            if y < top:
                column, y = column + 1, bottom - height
    x = geometry.right() - WIDTH - MARGIN - column * (WIDTH + GAP)
    return x, y


SETTINGS_WINDOW_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings_window.py")


def _open_settings() -> None:
    """設定画面を別プロセスで開く（通知は閉じない。二重起動は設定画面の側で防ぐ）。"""
    subprocess.Popen(
        [sys.executable, SETTINGS_WINDOW_SCRIPT],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        **popen_flags(detach=True),
    )


def _claude_executable() -> str:
    """解説の生成に使う claude の実行ファイル。見つからなければ空文字（解説ボタンを出さない）。

    VS Code 拡張などでは claude が PATH に無いため、Hook に渡される CLAUDE_CODE_EXECPATH を優先する。
    """
    path = os.environ.get("CLAUDE_CODE_EXECPATH", "")
    if path and is_executable(path):
        return path
    return shutil.which("claude") or ""


class NotificationWindow(QWidget):
    """1件分の通知ウィンドウ。常に最前面に表示され、閉じるボタンまたはクリックで消える。"""

    def __init__(
        self,
        title: str,
        body: str,
        description: str,
        command: str,
        bundle_id: str,
        slot: StackSlot,
        actions: bool = False,
        explain_input: str = "",
        markdown: str = "",
        plan_actions: bool = False,
        questions: list[dict] | None = None,
    ):
        super().__init__()
        self._bundle_id = bundle_id
        self._actions = actions
        self._plan_actions = plan_actions
        self._questions = questions or []  # [{"question", "header", "multiSelect", "labels"}]
        self._choice_groups: list[QButtonGroup] = []  # 質問ごとの選択肢ボタン
        self._submit_button: QPushButton | None = None
        self._explain_input = explain_input
        self._explain_button: QPushButton | None = None
        self._explain_view: QTextBrowser | None = None
        self._explain_process: QProcess | None = None
        self._explain_markdown = ""  # 表示中の解説。外観の切り替え時に書式を当て直すために持つ
        self._markdown = markdown  # 本文として表示する Markdown（質問・計画の承認待ち）
        self._markdown_view: QTextBrowser | None = None
        self._parent_pid = os.getppid()
        self._slot = slot
        self._stack_heights: list[int] | None = None
        self._closing = False
        self._move_anim: QPropertyAnimation | None = None
        self._close_anim: QPropertyAnimation | None = None

        # Qt.Tool不使用: 別プロセス・別NSApplicationとして生成される複数の通知window間で
        # WindowStaysOnTopHintの重なり順が不安定になる事象があったため、通常のQt.Windowで
        # 生成する（Dockアイコンが一瞬出るが、確実な最前面表示を優先する）。
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setFixedWidth(WIDTH)
        # 高さの計算にフォントサイズが効くため、レイアウトより先にスタイルを当てる
        self._init_highlight_params()
        self._apply_theme()
        QApplication.styleHints().colorSchemeChanged.connect(self._apply_theme)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 8, 8, 8)

        top_row = QHBoxLayout()
        title_label = QLabel(title)
        title_label.setObjectName("title")
        title_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        settings_button = QPushButton("⚙")
        settings_button.setFixedSize(20, 20)
        settings_button.setToolTip(tr("window.settings_tooltip"))
        settings_button.clicked.connect(_open_settings)
        close_button = QPushButton("✕")
        close_button.setFixedSize(20, 20)
        close_button.clicked.connect(
            lambda: self._animate_close(activate=False, result=RESULT_DISMISS)
        )
        top_row.addWidget(title_label)
        top_row.addStretch(1)
        top_row.addWidget(settings_button)
        top_row.addWidget(close_button)
        outer.addLayout(top_row)

        self._command_edit: QTextEdit | None = None
        if description:
            outer.addWidget(self._make_label(description, "description"))
        if command:
            self._command_edit = self._make_command_block(command)
            outer.addWidget(self._command_edit)
        if markdown:
            self._markdown_view = self._new_markdown_view("markdown")
            self._set_markdown(self._markdown_view, markdown)
            # クリックはコマンド欄と同じく本体クリック扱い（質問にはアプリ側で答える）。ホイールでスクロールできる
            self._markdown_view.viewport().installEventFilter(self)
            outer.addWidget(self._markdown_view)
        if body or not (description or command or markdown):
            outer.addWidget(self._make_label(body, "body"))
        outer.addStretch(1)
        if actions and self._questions:
            for question in self._questions:
                outer.addLayout(self._make_choice_list(question))
            outer.addLayout(self._make_submit_row())
        elif actions:
            outer.addLayout(self._make_plan_grid() if plan_actions else self._make_action_row())
        self._layout = outer
        self._fit_height(outer)

        self._init_gradient_params()
        self._gradient_phase = random.uniform(PHASE_RANGE_MIN, PHASE_RANGE_MAX)
        self._phase_step = random.uniform(*PHASE_STEP_RANGE)
        self._animation_timer = QTimer(self)
        self._animation_timer.setInterval(ANIMATION_INTERVAL_MS)
        self._animation_timer.timeout.connect(self._advance_animation)
        self._animation_timer.start()

        self._stack_timer = QTimer(self)
        self._stack_timer.setInterval(STACK_POLL_INTERVAL_MS)
        self._stack_timer.timeout.connect(self._check_stack_rank)
        self._stack_timer.start()

    @staticmethod
    def _make_label(text: str, name: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName(name)
        label.setTextFormat(Qt.PlainText)
        label.setWordWrap(True)
        label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        return label

    def _make_action_row(self) -> QHBoxLayout:
        """許可待ち用のボタン行。左端に「解説」（生成できる場合のみ）、右寄せで「キャンセル」「OK」。"""
        row = QHBoxLayout()
        row.setContentsMargins(0, 4, 4, 0)
        if self._explain_input and _claude_executable():
            self._explain_button = QPushButton(tr("button.explain"))
            self._explain_button.setObjectName("action")
            self._explain_button.setCursor(Qt.PointingHandCursor)
            self._explain_button.clicked.connect(self._start_explain)
            row.addWidget(self._explain_button)
        row.addStretch(1)
        for text, name, result in (
            (tr("button.cancel"), "action", RESULT_DENY),
            (tr("button.ok"), "primary", RESULT_ALLOW),
        ):
            button = QPushButton(text)
            button.setObjectName(name)
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(
                lambda _=False, r=result: self._animate_close(activate=False, result=r)
            )
            row.addWidget(button)
        return row

    def _make_plan_grid(self) -> QGridLayout:
        """計画の承認待ち用のボタン。「計画を続ける」と、切り替え先の権限モード別の承認を2列に並べる。"""
        grid = QGridLayout()
        grid.setContentsMargins(0, 4, 4, 0)
        grid.setSpacing(6)
        for i, (key, name, result) in enumerate(PLAN_BUTTONS):
            button = QPushButton(tr(key))
            button.setObjectName(name)
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(
                lambda _=False, r=result: self._animate_close(activate=False, result=r)
            )
            grid.addWidget(button, i // 2, i % 2)
        return grid

    def _make_choice_list(self, question: dict) -> QVBoxLayout:
        """質問1つ分の選択肢ボタン。単一選択は1つだけ、複数選択は何個でもオンにできる。"""
        column = QVBoxLayout()
        column.setContentsMargins(0, 4, 4, 0)
        column.setSpacing(4)
        heading = question.get("header") or question["question"]
        if question.get("multiSelect"):
            heading += tr("window.multi_select")
        column.addWidget(self._make_label(heading, "description"))
        group = QButtonGroup(self)
        group.setExclusive(not question.get("multiSelect"))
        for label in question["labels"]:
            button = QPushButton(label)
            button.setObjectName("choice")
            button.setCheckable(True)
            button.setCursor(Qt.PointingHandCursor)
            group.addButton(button)
            column.addWidget(button)
        group.buttonToggled.connect(self._update_submit_enabled)
        self._choice_groups.append(group)
        return column

    def _make_submit_row(self) -> QHBoxLayout:
        """選択肢の質問用のボタン行。すべての質問で1つ以上選ぶまで「回答する」は押せない。"""
        row = QHBoxLayout()
        row.setContentsMargins(0, 4, 4, 0)
        row.addStretch(1)
        self._submit_button = QPushButton(tr("button.submit"))
        self._submit_button.setObjectName("primary")
        self._submit_button.setCursor(Qt.PointingHandCursor)
        self._submit_button.setEnabled(False)
        self._submit_button.clicked.connect(self._submit_answers)
        row.addWidget(self._submit_button)
        return row

    def _update_submit_enabled(self, *_args) -> None:
        if self._submit_button is not None:
            self._submit_button.setEnabled(
                all(group.checkedButton() is not None for group in self._choice_groups)
            )

    def _submit_answers(self) -> None:
        """{質問文: 選んだ選択肢} を返す。複数選択はカンマ区切りでつなぐ（AskUserQuestion の answers の形式）。"""
        answers = {}
        for question, group in zip(self._questions, self._choice_groups):
            labels = [b.text() for b in group.buttons() if b.isChecked()]
            answers[question["question"]] = ", ".join(labels)
        result = RESULT_ANSWERS_PREFIX + json.dumps(answers, ensure_ascii=False)
        self._animate_close(activate=False, result=result)

    def _make_command_block(self, command: str) -> QTextEdit:
        """コマンド全文を等幅で表示する。QLabel は空白のない長い文字列を折り返せないため QTextEdit を使う。"""
        edit = QTextEdit()
        edit.setObjectName("command")
        edit.setReadOnly(True)
        edit.setFrameShape(QFrame.NoFrame)
        edit.setFocusPolicy(Qt.NoFocus)
        edit.setTextInteractionFlags(Qt.NoTextInteraction)
        edit.setLineWrapMode(QTextEdit.WidgetWidth)
        edit.setWordWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
        edit.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        edit.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        edit.setPlainText(command)
        # クリックは閉じる操作として扱う（ホイールでのスクロールはそのまま使える）
        edit.viewport().installEventFilter(self)
        return edit

    @staticmethod
    def _new_markdown_view(name: str) -> QTextBrowser:
        """Markdown を表示する欄（解説欄・質問や計画の本文欄で共通）。"""
        view = QTextBrowser()
        view.setObjectName(name)
        view.setFrameShape(QFrame.NoFrame)
        view.setOpenLinks(False)
        view.setWordWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
        view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        view.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        return view

    def _set_markdown(self, view: QTextBrowser, text: str) -> None:
        view.setMarkdown(text)
        self._polish_markdown(view)

    def _make_explain_view(self) -> QTextBrowser:
        """解説を表示する欄。本文欄やコマンド欄と違い、クリックしても閉じず文字を選択できる。"""
        view = self._new_markdown_view("explain")
        # ボタン行の直前（コマンド欄・本文の後、伸縮用の stretch の前）に差し込む
        self._layout.insertWidget(self._layout.count() - 2, view)
        view.show()  # 表示済みのウィンドウに後から加えた子は、明示しないと非表示のまま
        return view

    def _start_explain(self) -> None:
        executable = _claude_executable()
        if not executable or self._explain_process is not None:
            return
        self._explain_button.setEnabled(False)
        self._explain_button.setText(tr("button.explaining"))
        self._show_explain(tr("explain.generating"), markdown=False)

        process = QProcess(self)
        env = QProcessEnvironment.systemEnvironment()
        env.insert("HOOKNOTICE_DISABLED", "1")  # 生成用の claude から通知が出ないように
        process.setProcessEnvironment(env)
        # 作業中プロジェクトの CLAUDE.md を読み込ませない
        process.setWorkingDirectory(tempfile.gettempdir())
        process.finished.connect(self._on_explain_finished)
        process.errorOccurred.connect(self._on_explain_error)
        self._explain_process = process
        process.start(
            executable,
            [
                "-p",
                "--model", EXPLAIN_MODEL,
                "--tools", "",  # 解説のためにツールを実行させない
                "--setting-sources", "",  # ユーザー設定の Hook（この通知）を読み込ませない
                "--no-session-persistence",
                "--system-prompt", tr("explain.prompt"),
                self._explain_input,
            ],
        )
        process.closeWriteChannel()  # 閉じないと stdin 待ちで数秒遅れる

    def _on_explain_finished(self, exit_code: int, exit_status) -> None:
        process = self._explain_process
        if process is None or self._closing:
            return
        output = bytes(process.readAllStandardOutput()).decode("utf-8", "replace").strip()
        if exit_status == QProcess.NormalExit and exit_code == 0 and output:
            self._explain_process = None
            self._explain_button.setText(tr("button.explain"))
            self._show_explain(output, markdown=True)
            return
        error = bytes(process.readAllStandardError()).decode("utf-8", "replace").strip()
        self._fail_explain(error or output or tr("explain.exit_code", code=exit_code))

    def _on_explain_error(self, error) -> None:
        if error == QProcess.FailedToStart and not self._closing:
            self._fail_explain(tr("explain.start_failed"))

    def _fail_explain(self, reason: str) -> None:
        self._explain_process = None
        self._explain_button.setEnabled(True)  # 失敗時はもう一度押せるようにする
        self._explain_button.setText(tr("button.explain"))
        self._show_explain(tr("explain.failed", reason=reason[:300]), markdown=False)

    def _show_explain(self, text: str, markdown: bool) -> None:
        if self._explain_view is None:
            self._explain_view = self._make_explain_view()
        if markdown:
            self._explain_markdown = text
            self._set_markdown(self._explain_view, text)
        else:
            self._explain_view.setPlainText(text)
        # 高さを測り直して伸ばし、下に並ぶ通知にも新しい高さを知らせる
        self._fit_height(self._layout)
        self._init_gradient_params()
        self._slot.update_height(self.height())

    @staticmethod
    def _polish_markdown(view: QTextBrowser) -> None:
        """Qt の Markdown 表示は狭いカードには大きく、コードも目立たないため書式を整える。"""
        doc = view.document()
        doc.setIndentWidth(14)
        code_bg = THEMES[_current_theme()]["code_bg"]
        block = doc.begin()
        while block.isValid():
            cursor = QTextCursor(block)
            level = block.blockFormat().headingLevel()
            if level:
                cursor.select(QTextCursor.BlockUnderCursor)
                fmt = QTextCharFormat()
                fmt.setProperty(QTextFormat.FontPixelSize, EXPLAIN_HEADING_PX.get(level, 12))
                # Qt は見出しに文字サイズの段階（h1 は +3）も付けており、px 指定の上に上乗せされるので 0 にする
                fmt.setProperty(QTextFormat.FontSizeAdjustment, 0)
                cursor.mergeCharFormat(fmt)
            in_code_block = block.blockFormat().hasProperty(QTextFormat.BlockCodeFence)
            if in_code_block:
                block_fmt = QTextBlockFormat()
                block_fmt.setBackground(code_bg)
                block_fmt.setNonBreakableLines(False)  # 狭いカードで右端が切れないよう折り返す
                cursor.mergeBlockFormat(block_fmt)
            # 等幅指定の文字（`code` やコードブロック）を Menlo（Windows は Consolas）にし、背景を付ける
            it = block.begin()
            while not it.atEnd():
                frag = it.fragment()
                if frag.isValid() and (in_code_block or frag.charFormat().fontFixedPitch()):
                    frag_cursor = QTextCursor(doc)
                    frag_cursor.setPosition(frag.position())
                    frag_cursor.setPosition(frag.position() + frag.length(), QTextCursor.KeepAnchor)
                    fmt = QTextCharFormat()
                    fmt.setFontFamilies(["Menlo", "Monaco", "Consolas"])
                    fmt.setProperty(QTextFormat.FontPixelSize, 11)  # 本文（11px）とそろえる
                    if not in_code_block:  # コードブロックは行全体に背景を付けてある
                        fmt.setBackground(code_bg)
                    frag_cursor.mergeCharFormat(fmt)
                it += 1
            block = block.next()

    @staticmethod
    def _fit_text_edit(edit: QTextEdit, layout: QVBoxLayout) -> None:
        """QTextEdit 系の欄を、折り返した全文が収まる高さに固定する。"""
        edit.ensurePolished()
        margins = layout.contentsMargins()
        frame = edit.frameWidth() * 2 + 8  # 8: スタイルシートの padding 上下(左右)分
        text_width = WIDTH - margins.left() - margins.right() - frame
        doc = edit.document().clone(edit)
        doc.setDefaultFont(edit.font())
        doc.setDefaultTextOption(edit.document().defaultTextOption())
        doc.setTextWidth(text_width)
        edit.setFixedHeight(round(doc.size().height()) + frame)

    def _fit_height(self, layout: QVBoxLayout) -> None:
        """内容に合わせて高さを決める。画面に収まらない分は解説欄→コマンド欄の順に縮めてスクロールさせる。"""
        screen = QApplication.primaryScreen()
        max_height = (
            screen.availableGeometry().height() - 2 * MARGIN if screen else 10_000
        )
        self.ensurePolished()
        shrinkable = []  # (欄, 縮めてよい最小の高さ)。先頭から順に縮める
        for view in (self._explain_view, self._markdown_view):
            if view is not None:
                self._fit_text_edit(view, layout)
                shrinkable.append((view, EXPLAIN_MIN_HEIGHT))
        if self._command_edit is not None:
            self._fit_text_edit(self._command_edit, layout)
            shrinkable.append((self._command_edit, 40))
        layout.activate()
        # 折り返しラベルが無いと totalHeightForWidth は -1 になるため最小サイズも見る
        height = max(
            HEIGHT, layout.totalHeightForWidth(WIDTH), layout.minimumSize().height()
        )
        overflow = height - max_height
        for edit, min_height in shrinkable:
            if overflow <= 0:
                break
            current = edit.maximumHeight()
            reduced = max(min_height, current - overflow)
            edit.setFixedHeight(reduced)
            overflow -= current - reduced
        self.setFixedHeight(min(height, max_height))

    def eventFilter(self, watched, event) -> bool:  # noqa: N802 (Qt override)
        if event.type() == QEvent.MouseButtonPress:
            self._close_by_body_click()
            return True
        return super().eventFilter(watched, event)

    def update_stack_position(self, animate: bool) -> tuple[int, int] | None:
        """状態ファイルを読み直し、自分より新しい通知が変わっていれば表示位置を更新する。"""
        heights = self._slot.heights_newest_to_self()
        if heights is None or heights == self._stack_heights:
            return None
        self._stack_heights = heights
        screen = QApplication.primaryScreen()
        if screen is None:
            return None
        target = _stack_position(heights, screen.availableGeometry())
        if not animate:
            self.move(*target)
            return target
        if self._move_anim is not None:
            self._move_anim.stop()
        self._move_anim = QPropertyAnimation(self, b"pos", self)
        self._move_anim.setDuration(MOVE_ANIMATION_MS)
        self._move_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._move_anim.setStartValue(self.pos())
        self._move_anim.setEndValue(QPoint(*target))
        self._move_anim.start()
        return target

    def _check_stack_rank(self) -> None:
        if self._closing:
            return
        # 回答待ちの Hook がタイムアウト等で先に終了したら、答えても無意味なので閉じる
        if self._actions and parent_exited(self._parent_pid):
            self._animate_close(activate=False, result="")
            return
        self.update_stack_position(animate=True)

    def _animate_close(self, activate: bool, result: str) -> None:
        if self._closing:
            return
        self._closing = True
        self._stack_timer.stop()
        if self._explain_process is not None:
            self._explain_process.kill()
        if self._move_anim is not None:
            self._move_anim.stop()

        start = self.geometry()
        width = round(start.width() * CLICK_SHRINK_RATIO)
        height = round(start.height() * CLICK_SHRINK_RATIO)
        end = QRect(0, 0, width, height)
        end.moveCenter(start.center())

        # setFixedSize の固定を外さないと geometry アニメーションで縮められない
        self.setMinimumSize(0, 0)
        self._close_anim = QPropertyAnimation(self, b"geometry", self)
        self._close_anim.setDuration(CLICK_ANIMATION_MS)
        self._close_anim.setEasingCurve(QEasingCurve.OutQuad)
        self._close_anim.setStartValue(start)
        self._close_anim.setEndValue(end)
        self._close_anim.finished.connect(lambda: self._finish_close(activate, result))
        self._close_anim.start()

    def _finish_close(self, activate: bool, result: str) -> None:
        if self._actions and result:
            print(result, flush=True)  # 待っている hook_notify.py が読み取る
        if activate and self._bundle_id:
            activate_app(self._bundle_id)
        self.close()

    def _init_highlight_params(self) -> None:
        hue_jitter = random.uniform(-HUE_JITTER_DEGREES, HUE_JITTER_DEGREES)
        self._highlight_hue = (BASE_HUE_DEGREES + hue_jitter) % 360.0
        # 彩度・明度はテーマごとの範囲内での位置（0〜1）だけを決め、色はテーマ適用時に作る
        self._highlight_saturation_t = random.random()
        self._highlight_lightness_t = random.random()

    def _init_gradient_params(self) -> None:
        height = self.height()
        jx1 = random.uniform(-POINT_JITTER_RATIO, POINT_JITTER_RATIO) * WIDTH
        jy1 = random.uniform(-POINT_JITTER_RATIO, POINT_JITTER_RATIO) * height
        jx2 = random.uniform(-POINT_JITTER_RATIO, POINT_JITTER_RATIO) * WIDTH
        jy2 = random.uniform(-POINT_JITTER_RATIO, POINT_JITTER_RATIO) * height
        self._gradient_start = QPointF(jx1, jy1)
        self._gradient_end = QPointF(WIDTH + jx2, height + jy2)

    def _apply_theme(self, *_args) -> None:
        """現在の外観設定に合わせて配色を切り替える（表示中の切り替えにも呼ばれる）。"""
        theme = THEMES[_current_theme()]
        self.setStyleSheet(
            STYLE_SHEET.format(**{k: v for k, v in theme.items() if isinstance(v, str)})
        )
        self._base_color = QColor(theme["base"])
        self._border_color = theme["border"]
        s_min, s_max = theme["highlight_saturation"]
        l_min, l_max = theme["highlight_lightness"]
        self._highlight_color = QColor.fromHslF(
            self._highlight_hue / 360.0,
            s_min + (s_max - s_min) * self._highlight_saturation_t,
            l_min + (l_max - l_min) * self._highlight_lightness_t,
        )
        if self._explain_markdown:
            self._set_markdown(self._explain_view, self._explain_markdown)
        if self._markdown_view is not None:
            self._set_markdown(self._markdown_view, self._markdown)
        self.update()

    def _advance_animation(self) -> None:
        self._gradient_phase += self._phase_step
        if self._gradient_phase > PHASE_RANGE_MAX:
            self._gradient_phase = PHASE_RANGE_MIN
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt override)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), CORNER_RADIUS, CORNER_RADIUS)
        painter.setClipPath(path)

        gradient = QLinearGradient(self._gradient_start, self._gradient_end)
        center = self._gradient_phase
        for pos in GRADIENT_SAMPLE_POSITIONS:
            distance = abs(pos - center)
            intensity = _smoothstep(1.0 - distance / BAND_WIDTH)
            color = _lerp_color(self._base_color, self._highlight_color, intensity)
            gradient.setColorAt(pos, color)

        painter.fillPath(path, QBrush(gradient))
        if self._border_color is not None:
            painter.setClipping(False)
            painter.setPen(QPen(self._border_color, 1))
            # 線が半分はみ出さないよう 0.5px 内側に描く
            inner = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
            painter.drawRoundedRect(inner, CORNER_RADIUS, CORNER_RADIUS)
        painter.end()
        super().paintEvent(event)

    def mousePressEvent(self, event) -> None:  # noqa: N802 (Qt override)
        super().mousePressEvent(event)
        self._close_by_body_click()

    def _close_by_body_click(self) -> None:
        """本体クリックで閉じ、発火元アプリを前面化する。ボタン付きの通知は押し間違いで回答を逃さないよう閉じない。"""
        if self._actions:
            return
        self._animate_close(activate=True, result=RESULT_DISMISS)


def _parse_questions(text: str) -> list[dict]:
    """--questions の JSON を読む。形が崩れていれば空（従来どおりボタン無しの本文表示）にする。"""
    try:
        questions = json.loads(text) if text else []
    except ValueError:
        return []
    if not isinstance(questions, list):
        return []
    valid = [
        q for q in questions
        if isinstance(q, dict) and isinstance(q.get("question"), str)
        and isinstance(q.get("labels"), list) and q["labels"]
        and all(isinstance(label, str) for label in q["labels"])
    ]
    return valid if len(valid) == len(questions) else []


def main() -> int:
    use_utf8_stdio()  # 回答（日本語を含む JSON）を UTF-8 で hook_notify.py に渡す
    parser = argparse.ArgumentParser()
    parser.add_argument("--title", default="Claude Code")
    parser.add_argument("--body", default="")
    parser.add_argument("--description", default="")
    parser.add_argument("--command", default="")
    parser.add_argument("--bundle-id", default="")
    parser.add_argument("--actions", action="store_true")
    parser.add_argument("--explain-input", default="")
    parser.add_argument("--markdown", default="")
    parser.add_argument("--plan-actions", action="store_true")
    parser.add_argument("--questions", default="")  # 選択肢の質問の JSON（hook_notify.question_choices）
    args, _unknown = parser.parse_known_args()

    app = QApplication(sys.argv[:1])
    app.setQuitOnLastWindowClosed(True)

    slot = StackSlot()
    window = NotificationWindow(
        args.title,
        args.body,
        args.description,
        args.command,
        args.bundle_id,
        slot,
        actions=args.actions,
        explain_input=args.explain_input,
        markdown=args.markdown,
        plan_actions=args.plan_actions,
        questions=_parse_questions(args.questions),
    )
    slot.acquire(window.height())
    app.aboutToQuit.connect(slot.release)
    position = window.update_stack_position(animate=False)

    play_sound(CONFIG.sound_path())  # config.json の sound（設定画面で選ぶ）
    window.show()
    if position is not None:
        # macOS(Cocoa)はフレームレスウィンドウをshow()時に独自の位置へ配置し直す
        # ことがあるため、show()後に再度明示的に位置を固定する。
        window.move(*position)
    window.raise_()
    # 別プロセスとして生成される複数の通知間で最前面表示の反映が非同期になり、
    # 一部だけ画面に反映されない事象があったため、初回描画を同期的に確定させる。
    window.repaint()

    if os.environ.get("NOTIFY_DEBUG") == "1":
        def _debug_dump():
            print(
                f"pid={os.getpid()} heights={window._stack_heights} wanted={position} "
                f"actual_pos={(window.x(), window.y())} "
                f"frameGeometry={window.frameGeometry()} isVisible={window.isVisible()}",
                file=sys.stderr,
                flush=True,
            )

        QTimer.singleShot(500, _debug_dump)

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
