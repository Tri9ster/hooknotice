#!/usr/bin/env python3
"""Claude Code の Hooks から呼ばれる通知スクリプト（macOS専用）。

stdin から Hook ペイロード(JSON)を受け取り、通知の表示本体である `notify_window.py`
（PySide6製・別ファイル）を `uv` 管理の venv 経由で起動する。この薄いアダプタ自体は
標準ライブラリのみに依存する。許可待ち（permission_request）ではウィンドウの OK /
キャンセルを待って許可/拒否の決定を stdout に返し、それ以外は切り離して起動してすぐに
終了する。何が起きても Claude Code の動作を妨げないよう、常に exit 0 で終える。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time

from hooknotice_config import load_config
from messages import title as message_title, tr
from platform_support import (
    IS_WINDOWS,
    SUPPORTED,
    ask_dialog,
    bash_path,
    copy_to_clipboard,
    find_uv,
    locked_state,
    plugin_data_dir,
    popen_flags,
    state_dir,
    try_lock,
    use_utf8_stdio,
    venv_dir,
    venv_python,
)

HOOKNOTICE_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_DIR = venv_dir(HOOKNOTICE_DIR)  # プラグインなら <DATA>/venv
VENV_PYTHON = venv_python(HOOKNOTICE_DIR)
NOTIFY_WINDOW_SCRIPT = os.path.join(HOOKNOTICE_DIR, "notify_window.py")

# venv の準備（uv sync）。自動では実行せず、ダイアログで了承を得てから実行する。
# uv sync に成功した印を venv の中に置き、pyproject.toml / uv.lock の中身が変わっていれば更新を確認する
# （プラグインは更新のたびにファイルがコピーし直され更新日時が変わるので、印には中身のハッシュを書く）
SYNC_MARKER = os.path.join(VENV_DIR, ".hooknotice-synced")
SYNC_INPUTS = [os.path.join(HOOKNOTICE_DIR, name) for name in ("pyproject.toml", "uv.lock")]
SYNC_LOG = state_dir() / "sync.log"  # 最後の uv sync の出力
SETUP_LOCK = state_dir() / "setup.lock"  # 確認ダイアログ・同期中のプロセスが持つロック（二重に出さない）
SETUP_DECLINED = state_dir() / "setup.declined"  # 「今後確認しない」を選ばれたときに置く
PIP_REQUIREMENT = "PySide6-Essentials>=6.7"  # uv を使わずに pip で入れるときの指定（pyproject.toml と同じ）
# イベントごとのタイトル（messages.py のキー）
EVENT_TITLES = {
    "permission_request": "title.permission",
    "permission_prompt": "title.permission",
    "question": "title.question",
    "idle": "title.idle",
    "stop": "title.stop",
    "stop_failure": "title.stop_failure",
    "subagent_stop": "title.subagent_stop",
    "task_completed": "title.task_completed",
    "teammate_idle": "title.teammate_idle",
}

# Notification の種類（notification_type）ごとのタイトル。無い種類は NOTIFICATION_DEFAULT_TITLE
NOTIFICATION_TITLES = {
    name: f"title.{name}"
    for name in (
        "auth_success", "elicitation_dialog", "elicitation_url_dialog", "elicitation_complete",
        "elicitation_response", "agent_needs_input", "agent_completed", "quota_auto_resume_fired",
        "quota_auto_resume_stale", "quota_auto_resume_disabled",
    )
}
NOTIFICATION_TITLES.update({"permission_prompt": "title.permission", "idle_prompt": "title.idle"})
NOTIFICATION_DEFAULT_TITLE = "title.notification"

# 許可待ちのうち、ツールによってはタイトルを変える（本文は Markdown で整形して表示する）
TOOL_TITLES = {
    "AskUserQuestion": "title.question",
    "ExitPlanMode": "title.plan",
}

# notify_window.py に OK / キャンセルを出させ、回答を待つイベント
ACTION_EVENTS = ("permission_request",)
# 許可待ちでも、回答そのものがユーザー入力であるツール（OK/キャンセルでは答えられない）は通知のみ
NO_ACTION_TOOLS = ("AskUserQuestion",)
# 選択肢の質問は、選択肢をボタンにして回答を返す（選択肢を組み立てられなければ NO_ACTION_TOOLS どおり通知のみ）
QUESTION_TOOL = "AskUserQuestion"
# notify_window.py が回答を返すときの接頭辞。後ろに {質問文: 選んだ選択肢} の JSON が続く
ANSWERS_PREFIX = "answers "
# 計画の承認待ちは OK/キャンセルの代わりに、承認後の権限モード別のボタンを出す
PLAN_TOOL = "ExitPlanMode"
# notify_window.py の計画承認ボタンの結果 → 承認後に切り替える権限モード
PLAN_RESULT_MODES = {
    "plan_auto": "auto",
    "plan_accept_edits": "acceptEdits",
    "plan_default": "default",
}
# 「解説」で Claude に渡すツール入力の上限（Write の本文などが巨大な場合に切り詰める）
EXPLAIN_INPUT_MAX_CHARS = 8000

# コマンド欄の整形で、長い要素の先頭から1行ずつに分ける環境変数の代入（NAME=値 / NAME+=値）
_ASSIGNMENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\+?=")

# __CFBundleIdentifier が取れない場合の TERM_PROGRAM → bundle id の読み替え
TERM_PROGRAM_BUNDLE_IDS = {
    "Apple_Terminal": "com.apple.Terminal",
    "iTerm.app": "com.googlecode.iterm2",
    "vscode": "com.microsoft.VSCode",
}

# PermissionRequest の tool_input から本文に出す値を探すキー（先に見つかったものを使う）
TOOL_INPUT_SUMMARY_KEYS = (
    "command", "file_path", "notebook_path", "pattern", "url", "query", "description",
)


def read_stdin_payload() -> dict:
    if sys.stdin.isatty():
        return {}
    raw = sys.stdin.read().strip()
    if not raw:
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def host_bundle_id() -> str:
    """通知の発火元アプリ（ターミナル/VS Code等）の bundle id を推定する。"""
    bundle_id = os.environ.get("__CFBundleIdentifier", "")
    if bundle_id:
        return bundle_id
    return TERM_PROGRAM_BUNDLE_IDS.get(os.environ.get("TERM_PROGRAM", ""), "")


def _summarize_tool_input(tool_input) -> str:
    if not isinstance(tool_input, dict):
        return str(tool_input) if tool_input else ""
    for key in TOOL_INPUT_SUMMARY_KEYS:
        value = tool_input.get(key)
        if isinstance(value, str) and value:
            return value
    return json.dumps(tool_input, ensure_ascii=False) if tool_input else ""


def build_body(event: str, payload: dict) -> str:
    """ウィンドウ本文として、Claude Code が実際に尋ねている内容を組み立てる。"""
    body = ""
    if event in ("permission_request", "permission_prompt"):
        tool_name = payload.get("tool_name") or ""
        summary = _summarize_tool_input(payload.get("tool_input"))
        body = f"{tool_name}: {summary}" if tool_name and summary else tool_name or summary
    if not body:
        body = payload.get("message") or ""
    if not body and event == "stop":
        body = tr("body.stop_default")
    if not body and event == "notification":
        body = payload.get("title") or ""
    if not body:
        body = payload.get("cwd") or os.getcwd()

    return str(body).strip()  # 省略せず、改行もそのまま残す


def bash_command(event: str, payload: dict) -> tuple[str, str] | None:
    """Bash の許可待ちなら (説明, コマンド) を返す。説明は Claude が書いた description。"""
    if event not in ("permission_request", "permission_prompt"):
        return None
    tool_input = payload.get("tool_input")
    if payload.get("tool_name") != "Bash" or not isinstance(tool_input, dict):
        return None
    command = tool_input.get("command")
    if not isinstance(command, str) or not command.strip():
        return None
    description = tool_input.get("description")
    description = description.strip() if isinstance(description, str) else ""
    return description, format_command(command.strip())


class _Unsupported(Exception):
    """確実に解析できない書き方。整形せず元のまま表示する。"""


def _scan_command(command: str) -> list[tuple[str, str]]:
    """トップレベル（引用符・括弧の外）の語と演算子（; && || |）に分ける。

    戻り値は ("word", 元の文字列の一部) と ("op", 演算子) の列。語は元の文字列をそのまま
    切り出すので、引用符や中身は変わらない。解析に自信が持てない書き方は _Unsupported を投げる。
    """
    tokens: list[tuple[str, str]] = []
    n = len(command)
    i = 0
    depth = 0  # ( ) { } $( ) ${ } の入れ子の深さ
    word_start = -1

    def end_word(pos: int) -> None:
        nonlocal word_start
        if word_start >= 0:
            tokens.append(("word", command[word_start:pos]))
            word_start = -1

    def skip_quoted(pos: int, quote: str, escapes: bool) -> int:
        """pos は開き引用符の次。閉じ引用符の次の位置を返す。"""
        while pos < n:
            ch = command[pos]
            if escapes and ch == "\\":
                pos += 2
                continue
            if ch == quote:
                return pos + 1
            pos += 1
        raise _Unsupported("閉じていない引用符")

    while i < n:
        ch = command[i]
        if ch == "\n":
            raise _Unsupported("既に複数行")
        if depth == 0 and ch in " \t":
            end_word(i)
            i += 1
            continue
        if depth == 0 and ch == "#" and word_start < 0:
            raise _Unsupported("コメント")
        if depth == 0 and command.startswith(("&&", "||"), i):
            end_word(i)
            tokens.append(("op", command[i:i + 2]))
            i += 2
            continue
        if depth == 0 and ch == ";":
            if command.startswith(";;", i):
                raise _Unsupported("case 文")
            end_word(i)
            tokens.append(("op", ";"))
            i += 1
            continue
        # >| はリダイレクト、|& は扱わない
        if depth == 0 and ch == "|" and not (i > 0 and command[i - 1] == ">"):
            if command.startswith("|&", i):
                raise _Unsupported("|&")
            end_word(i)
            tokens.append(("op", "|"))
            i += 1
            continue

        if word_start < 0:
            word_start = i
        if ch == "\\":
            if i + 1 < n and command[i + 1] == "\n":
                raise _Unsupported("既に複数行")
            i += 2
        elif ch == "'":
            i = skip_quoted(i + 1, "'", escapes=False)
        elif ch == "$" and command.startswith("$'", i):
            i = skip_quoted(i + 2, "'", escapes=True)
        elif ch == '"':
            i = skip_quoted(i + 1, '"', escapes=True)
        elif ch == "`":
            i = skip_quoted(i + 1, "`", escapes=True)
        elif ch == "<" and command.startswith("<<", i) and not command.startswith("<<<", i):
            raise _Unsupported("ヒアドキュメント")
        elif ch in "({":
            depth += 1
            i += 1
        elif ch in ")}":
            depth -= 1
            if depth < 0:
                raise _Unsupported("対応しない括弧")
            i += 1
        else:
            i += 1
    if depth != 0:
        raise _Unsupported("閉じていない括弧")
    end_word(n)
    return tokens


def _format_element(segments: list[list[str]], line_limit: int) -> list[str]:
    """&& / || の間の1要素（パイプでつながったコマンド）を行に分ける。"""
    one_line = " | ".join(" ".join(words) for words in segments)
    if len(one_line) <= line_limit:
        return [one_line]
    first = segments[0]
    n_assign = 0
    while n_assign < len(first) and _ASSIGNMENT_RE.match(first[n_assign]):
        n_assign += 1
    if n_assign == len(first) and len(segments) == 1:
        return [one_line]  # S=... のような代入だけの要素は分けない
    lines = list(first[:n_assign])
    indent = "  " if n_assign else ""
    lines.append(indent + " ".join(first[n_assign:]))
    lines += ["  | " + " ".join(words) for words in segments[1:]]
    return lines


def format_command(command: str, line_limit: int | None = None) -> str:
    """通知のコマンド欄用に、ワンライナーを意味を変えずに複数行へ整形する。

    変えるのは空白・改行・行継続の \\ だけ。; は行末に残して空行で区切り、&& / || は行末に残す。
    長い要素は、先頭の環境変数の代入を1行ずつ、パイプの2段目以降を次の行に置く。
    解析できない書き方や、整形結果が bash の構文チェックを通らない場合は元のまま返す。
    長い要素とみなす文字数（line_limit）は、省略時は設定ファイルの command_line_limit。
    """
    if line_limit is None:
        line_limit = load_config().command_line_limit
    try:
        tokens = _scan_command(command)
    except _Unsupported:
        return command
    if not any(kind == "op" for kind, _ in tokens):
        if len(command) <= line_limit:
            return command

    blocks: list[str] = []  # ; で区切ったまとまり。空行をはさんで並べる
    block: list[str] = []  # まとまりの中の要素（&& / || でつながる）
    segments: list[list[str]] = [[]]  # 要素の中のパイプの各段
    for kind, text in tokens + [("op", "")]:  # "" は末尾の印
        if kind == "word":
            segments[-1].append(text)
            continue
        if text == "|":
            if not segments[-1]:
                return command
            segments.append([])
            continue
        if not segments[-1]:
            if text == "" and not block and len(segments) == 1:
                break  # 末尾が ; で終わっている
            return command
        lines = _format_element(segments, line_limit)
        segments = [[]]
        if text in ("&&", "||"):
            lines[-1] += f" {text} \\"
        elif text == ";":
            lines[-1] += ";"
        block.append(" \\\n".join(lines))
        if text in (";", ""):
            blocks.append("\n".join(block))
            block = []
    formatted = "\n\n".join(blocks)

    # 念のため、整形結果が bash の構文として正しいかを確かめる（-n は実行しない）。bash が無ければ整形しない
    bash = bash_path()
    if not bash:
        return command
    try:
        check = subprocess.run(
            [bash, "-n", "-c", formatted],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=2,
            **popen_flags(detach=False),
        )
    except (OSError, subprocess.SubprocessError):
        return command
    return formatted if check.returncode == 0 else command


def sync_inputs_hash() -> str:
    """pyproject.toml / uv.lock の中身のハッシュ（印ファイルに書き、次回と比べる）。"""
    digest = hashlib.sha256()
    for path in SYNC_INPUTS:
        try:
            with open(path, "rb") as f:
                digest.update(f.read())
        except OSError:
            pass
        digest.update(b"\0")
    return digest.hexdigest()


def needs_sync() -> bool:
    """venv が無い、または uv sync したときから pyproject.toml / uv.lock が変わっていれば真。

    pip などで自分で作った venv（印ファイルが無い）は、更新の確認をしない。
    印ファイルが空（ハッシュを書く前の版で作ったもの）なら、従来どおり更新日時で比べる。
    """
    if not os.path.exists(VENV_PYTHON):
        return True
    try:
        with open(SYNC_MARKER, encoding="utf-8") as f:
            recorded = f.read().strip()
    except OSError:
        return False
    if recorded:
        return recorded != sync_inputs_hash()
    synced = os.path.getmtime(SYNC_MARKER)
    return any(os.path.exists(path) and os.path.getmtime(path) > synced for path in SYNC_INPUTS)


def sync_command() -> str:
    """確認ダイアログに見せる、実行するコマンド。"""
    if plugin_data_dir():
        env = f'set UV_PROJECT_ENVIRONMENT={VENV_DIR}' if IS_WINDOWS else f'UV_PROJECT_ENVIRONMENT="{VENV_DIR}"'
        separator = "\n  " if IS_WINDOWS else " "
        return f'  cd "{HOOKNOTICE_DIR}"\n  {env}{separator}uv sync --frozen'
    return f'  cd "{HOOKNOTICE_DIR}"\n  uv sync --frozen'


def start_setup() -> None:
    """準備の確認ダイアログを切り離して出す（hook_notify.py --setup）。「今後確認しない」を選ばれていれば出さない。"""
    if SETUP_DECLINED.exists():
        return
    spawn([sys.executable, os.path.abspath(__file__), "--setup"])


def _uv_missing_steps() -> str:
    """uv が無いときに見せる、uv の入れ方と pip で入れる手順。"""
    return tr("setup.steps_win" if IS_WINDOWS else "setup.steps_mac", venv=VENV_DIR, req=PIP_REQUIREMENT)


def _ask_setup(message: str, buttons: list[str], timeout: int = 0) -> str:
    """準備の確認ダイアログを出す（Windows のボタンの対応の書き添えも今の言語にする）。"""
    hints = (tr("dialog.hint2"), tr("dialog.hint3"))
    return ask_dialog(tr("setup.title"), message, buttons, timeout=timeout, button_hints=hints)


def run_setup() -> int:
    """--setup の本体。uv sync を実行してよいかをダイアログで聞き、了承されたときだけ実行する。"""
    lock = try_lock(SETUP_LOCK)
    if lock is None:
        return 0  # 別のセッションが確認中・同期中
    with lock:
        if not needs_sync() or SETUP_DECLINED.exists():
            return 0
        uv = find_uv()
        decline, copy_steps, run = tr("setup.decline"), tr("setup.copy_steps"), tr("setup.run")
        if not uv:
            steps = _uv_missing_steps()
            answer = _ask_setup(
                tr("setup.uv_missing", need=tr("setup.need_library"), steps=steps),
                [decline, tr("setup.close"), copy_steps],
            )
            if answer == copy_steps:
                copy_to_clipboard(steps)
            elif answer == decline:
                SETUP_DECLINED.touch()
            return 0
        reason = tr("setup.updated" if os.path.exists(VENV_PYTHON) else "setup.need_library")
        answer = _ask_setup(
            tr("setup.confirm", reason=reason, command=sync_command()),
            [decline, tr("setup.not_now"), run],
        )
        if answer == decline:
            SETUP_DECLINED.touch()
        if answer != run:
            return 0
        if run_sync(uv):
            _ask_setup(tr("setup.done"), [tr("button.ok")], timeout=15)
        else:
            _ask_setup(tr("setup.failed", log=SYNC_LOG), [tr("button.ok")])
    return 0


def run_sync(uv: str) -> bool:
    """uv sync --frozen を実行し、出力を sync.log に残す。成功したら印ファイルを作って真を返す。"""
    env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}  # 呼び出し元の venv を使わせない
    if plugin_data_dir():
        env["UV_PROJECT_ENVIRONMENT"] = VENV_DIR  # venv は本体ではなく、更新しても残る DATA に作る
        os.makedirs(os.path.dirname(VENV_DIR), exist_ok=True)
    SYNC_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(SYNC_LOG, "w", encoding="utf-8") as log:
        log.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} uv sync --frozen ({HOOKNOTICE_DIR} -> {VENV_DIR})\n")
        log.flush()
        try:
            code = subprocess.run(
                [uv, "sync", "--frozen"],
                cwd=HOOKNOTICE_DIR,
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=subprocess.STDOUT,
                **popen_flags(detach=False),
            ).returncode
        except OSError as e:
            log.write(f"{e}\n")
            code = 1
        log.write(tr("setup.exit_code", code=code) + "\n")
    if code != 0 or not os.path.exists(VENV_PYTHON):
        return False
    with open(SYNC_MARKER, "w", encoding="utf-8") as f:
        f.write(sync_inputs_hash() + "\n")
    return True


def spawn(args: list) -> None:
    subprocess.Popen(
        args,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        **popen_flags(detach=True),
    )


def _code_fence(text: str) -> str:
    """text の中に現れるより長いバッククォートの列を、コードブロックの囲みに使う。"""
    longest = max((len(run) for run in re.findall(r"`+", text)), default=0)
    return "`" * max(3, longest + 1)


def question_markdown(tool_input) -> str:
    """AskUserQuestion の質問と選択肢を Markdown にする。組み立てられなければ空文字。"""
    questions = tool_input.get("questions") if isinstance(tool_input, dict) else None
    if not isinstance(questions, list):
        return ""
    parts = []
    for q in questions:
        if not isinstance(q, dict) or not isinstance(q.get("question"), str):
            continue
        header = q.get("header")
        line = f"**[{header}]** " if isinstance(header, str) and header else ""
        line += q["question"].strip()
        if q.get("multiSelect") is True:
            line += " " + tr("body.multi_select_md")
        lines = [line, ""]
        options = q.get("options") if isinstance(q.get("options"), list) else []
        number = 0
        for option in options:
            if not isinstance(option, dict) or not isinstance(option.get("label"), str):
                continue
            number += 1
            item = f"{number}. **{option['label'].strip()}**"
            description = option.get("description")
            if isinstance(description, str) and description.strip():
                item += f" — {description.strip()}"
            lines.append(item)
            preview = option.get("preview")
            if isinstance(preview, str) and preview.strip():
                # 番号付きリストの項目の中に入れるため、3文字字下げしたコードブロックにする
                fence = _code_fence(preview)
                lines.append("")
                lines += ["   " + row for row in [fence, *preview.rstrip().splitlines(), fence]]
                lines.append("")
        parts.append("\n".join(lines).rstrip())
    return "\n\n---\n\n".join(parts)


def question_choices(tool_input) -> list[dict]:
    """AskUserQuestion の質問ごとの選択肢（ボタンにする label）を返す。

    選択肢の無い質問が1つでもあればボタンでは答えきれないので空リストにする。
    """
    questions = tool_input.get("questions") if isinstance(tool_input, dict) else None
    if not isinstance(questions, list) or not questions:
        return []
    choices = []
    for q in questions:
        if not isinstance(q, dict) or not isinstance(q.get("question"), str):
            return []
        options = q.get("options") if isinstance(q.get("options"), list) else []
        labels = [
            o["label"] for o in options
            if isinstance(o, dict) and isinstance(o.get("label"), str) and o["label"].strip()
        ]
        if not labels:
            return []
        header = q.get("header")
        choices.append({
            "question": q["question"],
            "header": header if isinstance(header, str) else "",
            "multiSelect": q.get("multiSelect") is True,
            "labels": labels,
        })
    return choices


def tool_markdown(event: str, payload: dict) -> str:
    """質問・計画の承認待ちなら、本文として表示する Markdown を返す。該当しなければ空文字。"""
    if event not in ("permission_request", "permission_prompt"):
        return ""
    tool_name = payload.get("tool_name")
    tool_input = payload.get("tool_input")
    if tool_name == "AskUserQuestion":
        return question_markdown(tool_input)
    if tool_name == "ExitPlanMode" and isinstance(tool_input, dict):
        plan = tool_input.get("plan")
        return plan.strip() if isinstance(plan, str) else ""
    return ""


def stop_markdown(event: str, payload: dict) -> str:
    """作業完了（Stop）なら、本文として表示する Claude の最後の応答を返す。該当しなければ空文字。"""
    if event != "stop":
        return ""
    message = payload.get("last_assistant_message")
    return message.strip() if isinstance(message, str) else ""


def stop_failure_markdown(event: str, payload: dict) -> str:
    """エラーで停止（StopFailure）なら、エラーの種類・詳細・エラー文を Markdown にする。該当しなければ空文字。"""
    if event != "stop_failure":
        return ""
    lines = []
    error = payload.get("error")
    if isinstance(error, str) and error:
        lines.append(tr("body.error_type", error=error))
    details = payload.get("error_details")
    if isinstance(details, str) and details.strip():
        lines.append(tr("body.error_details", details=details.strip()))
    message = payload.get("last_assistant_message")
    if isinstance(message, str) and message.strip():
        lines += ["", message.strip()]
    return "\n\n".join(line for line in lines if line) if lines else tr("body.error_default")


def _text(payload: dict, key: str) -> str:
    value = payload.get(key)
    return value.strip() if isinstance(value, str) else ""


def agent_markdown(event: str, payload: dict) -> str:
    """サブエージェント・タスク系の本文（Markdown）。該当しなければ空文字。"""
    if event == "subagent_stop":
        parts = []
        if _text(payload, "agent_type"):
            parts.append(tr("body.agent_type", agent=_text(payload, "agent_type")))
        parts.append(_text(payload, "last_assistant_message") or tr("body.subagent_default"))
        return "\n\n".join(parts)
    if event == "task_completed":
        parts = [f"**{_text(payload, 'task_subject') or tr('body.task_default')}**"]
        if _text(payload, "task_description"):
            parts.append(_text(payload, "task_description"))
        if _text(payload, "teammate_name"):
            parts.append(tr("body.task_owner", name=_text(payload, "teammate_name")))
        return "\n\n".join(parts)
    if event == "teammate_idle":
        name = _text(payload, "teammate_name") or tr("body.teammate_default")
        team = _text(payload, "team_name")
        return tr("body.teammate_idle", name=name) + (tr("body.teammate_team", team=team) if team else "")
    return ""


def scene_key(event: str, payload: dict) -> str:
    """設定（config.json の notify）で、この通知を出すかを判断するキー。空文字は常に出す（手動テスト用）。"""
    if event in ("permission_request", "permission_prompt") and payload.get("hook_event_name") != "Notification":
        tool_name = payload.get("tool_name")
        if tool_name == QUESTION_TOOL:
            return "question"
        if tool_name == PLAN_TOOL:
            return "plan"
        return "permission_request" if event == "permission_request" else "permission_prompt"
    if event == "notification":
        return str(payload.get("notification_type") or "")
    if event in ("subagent_stop", "task_completed", "teammate_idle"):
        return event
    return {"stop": "stop", "stop_failure": "stop_failure", "idle": "idle_prompt"}.get(event, "")


def explain_input(payload: dict) -> str:
    """「解説」ボタンで Claude に渡す、許可を求められている操作の内容。"""
    tool_input = json.dumps(payload.get("tool_input"), ensure_ascii=False, indent=2)
    if len(tool_input) > EXPLAIN_INPUT_MAX_CHARS:
        tool_input = tool_input[:EXPLAIN_INPUT_MAX_CHARS] + tr("explain.truncated")
    return tr(
        "explain.input",
        tool=payload.get("tool_name") or tr("explain.unknown_tool"),
        cwd=payload.get("cwd") or os.getcwd(),
        input=tool_input,
    )


def permission_decision(result: str, payload: dict | None = None) -> dict | None:
    """ウィンドウの回答を PermissionRequest の決定に変換する。None はターミナルに委ねる。"""
    payload = payload or {}
    plan = payload.get("tool_name") == PLAN_TOOL
    if result.startswith(ANSWERS_PREFIX):
        try:
            answers = json.loads(result[len(ANSWERS_PREFIX):])
        except ValueError:
            return None
        tool_input = payload.get("tool_input")
        if not isinstance(answers, dict) or not isinstance(tool_input, dict):
            return None
        # 元の質問をそのまま返し、answers を足すと質問を出さずに回答済みとして進む
        decision = {"behavior": "allow", "updatedInput": {**tool_input, "answers": answers}}
    elif result == "allow":
        decision = {"behavior": "allow"}
    elif result in PLAN_RESULT_MODES:
        mode = PLAN_RESULT_MODES[result]
        tool_input = payload.get("tool_input")
        decision = {
            "behavior": "allow",
            # ExitPlanMode は allow だけでは採用されず、updatedInput（元の入力をそのまま）を組にする必要がある
            "updatedInput": tool_input if isinstance(tool_input, dict) else {},
            "updatedPermissions": [
                {"type": "setMode", "mode": mode, "destination": "session"}
            ],
        }
    elif result == "deny":
        decision = {"behavior": "deny", "message": tr("deny.plan" if plan else "deny.permission")}
    else:
        return None
    return {
        "hookSpecificOutput": {
            "hookEventName": "PermissionRequest",
            "decision": decision,
        }
    }


ANSWER_POLL_SECONDS = 0.5  # ターミナル側での回答を確かめる間隔
TRANSCRIPT_TAIL_BYTES = 4 * 1024 * 1024  # 許可待ちのツール呼び出しを探す範囲（会話の記録の末尾）


def _transcript_entries(path: str, start: int):
    """会話の記録（JSON Lines）を start バイト目から読み、(読み終えた位置, 各行の dict) を返す。"""
    with open(path, "rb") as f:
        f.seek(0, os.SEEK_END)
        end = f.tell()
        f.seek(start)
        data = f.read(end - start)
    end = start + data.rfind(b"\n") + 1  # 書きかけの最後の行は次回に読む
    entries = []
    for line in data[: end - start].splitlines():
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if isinstance(entry, dict):
            entries.append(entry)
    return end, entries


def _content_items(entry: dict, item_type: str):
    message = entry.get("message")
    content = message.get("content") if isinstance(message, dict) else None
    if isinstance(content, list):
        for item in content:
            if isinstance(item, dict) and item.get("type") == item_type:
                yield item


class AnswerWatcher:
    """許可待ちにターミナル側で答えられたかを、会話の記録（transcript）で確かめる。

    答えると、そのツール呼び出し（tool_use）の結果（tool_result）が記録される（拒否はすぐ、許可は
    ツールの実行後）。呼び出し自体の書き込みは Hook の開始より遅れることがあるので、待つ間も探し続ける。
    該当する呼び出しが見つからないとき（記録の形式が変わった場合など）は、答えられていない扱いにして
    従来どおり通知する。
    """

    def __init__(self, payload: dict):
        self.path = ""
        self.offset = 0
        self.tool_use_id = ""
        self.name, self.tool_input = payload.get("tool_name"), payload.get("tool_input")
        path = payload.get("agent_transcript_path") or payload.get("transcript_path")
        if not isinstance(path, str) or not os.path.isfile(path):
            return
        try:
            start = max(0, os.path.getsize(path) - TRANSCRIPT_TAIL_BYTES)
            self.offset, entries = _transcript_entries(path, start)
        except OSError:
            return
        self.path = path
        # 同じ内容の呼び出しが過去にもあり得るので、すでに記録済みのものは未回答のものだけを候補にする
        pending = []
        for entry in entries:
            for item in _content_items(entry, "tool_use"):
                if self._matches(item):
                    pending.append(item.get("id"))
            for item in _content_items(entry, "tool_result"):
                if item.get("tool_use_id") in pending:
                    pending.remove(item.get("tool_use_id"))
        if pending:
            self.tool_use_id = pending[0]  # 許可は呼び出し順に聞かれるので、最も古い未回答のもの

    def _matches(self, item: dict) -> bool:
        return item.get("name") == self.name and item.get("input") == self.tool_input

    def answered(self) -> bool:
        if not self.path:
            return False
        try:
            self.offset, entries = _transcript_entries(self.path, self.offset)
        except OSError:
            return False
        for entry in entries:
            for item in _content_items(entry, "tool_use"):
                if not self.tool_use_id and self._matches(item):
                    self.tool_use_id = item.get("id")
            for item in _content_items(entry, "tool_result"):
                if self.tool_use_id and item.get("tool_use_id") == self.tool_use_id:
                    return True
        return False


def ask(args: list, payload: dict) -> None:
    """ウィンドウが閉じられるまで待ち、ボタンで回答されたら決定を stdout に出力する。

    表示中にターミナル側で答えられたら、何も出力せずに終了する（ウィンドウはそれに気づいて閉じる）。
    """
    watcher = AnswerWatcher(payload)
    proc = subprocess.Popen(
        args + ["--actions"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        encoding="utf-8",
        **popen_flags(detach=False),
    )
    while True:
        try:
            stdout, _ = proc.communicate(timeout=ANSWER_POLL_SECONDS)
            break
        except subprocess.TimeoutExpired:
            if watcher.answered():
                return  # Hook が終わると、ウィンドウは起動元の終了に気づいて自分で閉じる
    decision = permission_decision(stdout.strip(), payload)
    if decision is not None:
        print(json.dumps(decision, ensure_ascii=False), flush=True)


def notify(event: str, payload: dict) -> None:
    if not os.path.exists(VENV_PYTHON):
        start_setup()  # 準備がまだ。uv sync を実行してよいか確認する（今回の通知は出せない）
        return

    title = message_title(EVENT_TITLES[event]) if event in EVENT_TITLES else "Claude Code"
    if event == "notification":
        title = message_title(NOTIFICATION_TITLES.get(payload.get("notification_type"), NOTIFICATION_DEFAULT_TITLE))
    if event == "subagent_stop" and _text(payload, "agent_type"):
        title += tr("title.subagent_suffix", agent=_text(payload, "agent_type"))
    markdown = (
        tool_markdown(event, payload)
        or stop_markdown(event, payload)
        or stop_failure_markdown(event, payload)
        or agent_markdown(event, payload)
    )
    if markdown and payload.get("tool_name") in TOOL_TITLES:
        title = message_title(TOOL_TITLES[payload["tool_name"]])
    args = [
        VENV_PYTHON,
        NOTIFY_WINDOW_SCRIPT,
        "--title", title,
        "--bundle-id", host_bundle_id(),
    ]
    bash = bash_command(event, payload)
    if bash is not None:
        description, command = bash
        args += ["--description", description, "--command", command]
    elif markdown:
        args += ["--markdown", markdown]
    else:
        args += ["--body", build_body(event, payload)]
    tool_name = payload.get("tool_name")
    choices = question_choices(payload.get("tool_input")) if tool_name == QUESTION_TOOL else []
    if event in ACTION_EVENTS and tool_name == PLAN_TOOL:
        ask(args + ["--plan-actions"], payload)
    elif event in ACTION_EVENTS and choices:
        ask(args + ["--questions", json.dumps(choices, ensure_ascii=False)], payload)
    elif event in ACTION_EVENTS and tool_name not in NO_ACTION_TOOLS:
        ask(args + ["--explain-input", explain_input(payload)], payload)
    else:
        spawn(args)


# Claude Code 自身が約6秒（idle_prompt は約60秒）待ってから出す通知。hooknotice の待ち時間は足さない
NO_DELAY_NOTIFICATIONS = ("permission_prompt", "idle_prompt", "elicitation_dialog", "elicitation_url_dialog")
PROMPTS_PATH = state_dir() / "prompts.json"  # セッションごとの最後のプロンプト送信時刻
PROMPT_RECORD_TTL = 24 * 60 * 60  # これより古い記録は書き込みのたびに消す


def reading_text(event: str, payload: dict) -> str:
    """待ち時間を文字数から決めるときに数える本文（VS Code 側でユーザーが読む内容）。"""
    markdown = (
        tool_markdown(event, payload) or stop_markdown(event, payload)
        or stop_failure_markdown(event, payload) or agent_markdown(event, payload)
    )
    if markdown:
        return markdown
    command = bash_command(event, payload)
    if command:
        return "\n".join(command)
    tool_input = payload.get("tool_input")
    if event == "permission_request" and isinstance(tool_input, dict):
        # ファイルの編集・作成は、VS Code が差分や中身を見せる
        edits = tool_input.get("edits") if isinstance(tool_input.get("edits"), list) else [tool_input]
        parts = [
            value
            for edit in edits if isinstance(edit, dict)
            for value in (edit.get("old_string"), edit.get("new_string"), edit.get("content"))
            if isinstance(value, str)
        ]
        if parts:
            return "\n".join(parts)
    return build_body(event, payload)


def count_chars(text: str) -> int:
    """読む文字数（空白・改行は数えない）。"""
    return len(re.sub(r"\s", "", text))


def needs_delay(event: str, payload: dict) -> bool:
    """放置されたかを見るために、通知を出す前に待つ必要があるか。"""
    return not (event == "notification" and payload.get("notification_type") in NO_DELAY_NOTIFICATIONS)


def _read_prompts(f) -> dict:
    f.seek(0)
    try:
        data = json.loads(f.read() or "{}")
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


def record_prompt(payload: dict) -> None:
    """プロンプトが送られた時刻をセッションごとに記録する（UserPromptSubmit）。"""
    session_id = payload.get("session_id")
    if not isinstance(session_id, str) or not session_id:
        return
    now = time.time()
    try:
        PROMPTS_PATH.parent.mkdir(parents=True, exist_ok=True)
        PROMPTS_PATH.touch(exist_ok=True)
        with locked_state(PROMPTS_PATH) as f:
            prompts = {
                k: v for k, v in _read_prompts(f).items()
                if isinstance(v, (int, float)) and now - v < PROMPT_RECORD_TTL
            }
            prompts[session_id] = now
            f.seek(0)
            f.truncate()
            f.write(json.dumps(prompts))
    except OSError:
        pass


def prompted_since(payload: dict, since: float) -> bool:
    """since 以降に、同じセッションで新しいプロンプトが送られたか。"""
    session_id = payload.get("session_id")
    if not isinstance(session_id, str) or not session_id or not PROMPTS_PATH.exists():
        return False
    try:
        with locked_state(PROMPTS_PATH) as f:
            sent = _read_prompts(f).get(session_id)
    except OSError:
        return False
    return isinstance(sent, (int, float)) and sent >= since


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--event", default="permission_request")
    parser.add_argument("--setup", action="store_true", help=argparse.SUPPRESS)  # 内部用: 準備の確認ダイアログ
    args = parser.parse_args()
    use_utf8_stdio()  # Claude Code とは UTF-8 の JSON でやりとりする
    if args.setup:
        return run_setup()

    payload = read_stdin_payload()
    if not SUPPORTED or os.environ.get("HOOKNOTICE_DISABLED") == "1":
        return 0
    if args.event == "prompt_submit":
        record_prompt(payload)
        return 0
    if args.event == "session_start":
        try:
            if needs_sync():
                start_setup()  # uv sync を実行してよいかダイアログで確認する（自動では実行しない）
        except Exception:
            pass  # 確認に失敗しても Claude Code の起動を妨げない
        return 0
    config = load_config()
    key = scene_key(args.event, payload)
    if key and not config.enabled(key):
        return 0  # 設定でオフ。許可待ちなら何も出力しない＝通常どおりターミナル側のダイアログで答える
    delay = config.delay_for(count_chars(reading_text(args.event, payload))) if needs_delay(args.event, payload) else 0
    if delay:
        # 放置されたときだけ出す。許可待ちは、待っている間にターミナル側で答えられたら出さない
        # （Claude Code は答えられても Hook を終了させないので、会話の記録で回答を確かめる）。
        # それ以外は、待っている間にプロンプトが送られたら出さない
        started = time.time()
        if args.event in ACTION_EVENTS:
            watcher = AnswerWatcher(payload)
            while time.time() - started < delay:
                time.sleep(ANSWER_POLL_SECONDS)
                if watcher.answered():
                    return 0
        else:
            time.sleep(delay)
            if prompted_since(payload, started):
                return 0
    try:
        notify(args.event, payload)
    except Exception:
        pass  # 通知に失敗しても Claude Code をブロックしない
    return 0


if __name__ == "__main__":
    sys.exit(main())
