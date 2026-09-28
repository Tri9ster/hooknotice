#!/usr/bin/env python3
"""hooknotice の設定画面（PySide6）。

通知の ⚙ ボタンと、スラッシュコマンド /hooknotice-settings から開く。config.json だけを書き換え、
通知は1件ごとに設定を読み直すので、保存すると次の通知から反映される（Claude Code の再起動は不要）。
"""
from __future__ import annotations

import os
import subprocess
import sys

from hooknotice_config import (
    DEFAULT_DELAY_SECONDS,
    DEFAULT_READING_CPM,
    DEFAULT_WIDTH,
    DELAY_RANGE,
    LANGUAGES,
    LINE_LIMIT_RANGE,
    READING_CPM_RANGE,
    READING_DELAY_MAX,
    SCENES,
    WIDTH_RANGE,
    auto_line_limit,
    load_config,
    save_config,
)
from messages import title as message_title, tr
from platform_support import (
    SOUND_FILE_SUFFIXES,
    list_system_sounds,
    play_sound,
    popen_flags,
    state_dir,
    system_sound_dir,
    system_sound_path,
    use_utf8_stdio,
)

from PySide6.QtCore import QLockFile, Qt
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

NOTIFY_WINDOW_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "notify_window.py")
LOCK_PATH = state_dir() / "settings.lock"


class SettingsWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(tr("settings.window_title"))
        self.setMinimumWidth(520)
        config = load_config()

        outer = QVBoxLayout(self)
        outer.addWidget(self._make_display_group(config))
        outer.addWidget(self._make_sound_group(config))
        outer.addWidget(self._make_scene_group(config), 1)

        self._status = QLabel("")
        self._status.setStyleSheet("color: gray;")
        buttons = QHBoxLayout()
        test_button = QPushButton(tr("settings.test"))
        test_button.setToolTip(tr("settings.test_tooltip"))
        test_button.clicked.connect(self._show_test)
        save_button = QPushButton(tr("settings.save"))
        save_button.setDefault(True)
        save_button.clicked.connect(self._save)
        close_button = QPushButton(tr("settings.close"))
        close_button.clicked.connect(self.close)
        buttons.addWidget(test_button)
        buttons.addWidget(self._status, 1)
        buttons.addWidget(close_button)
        buttons.addWidget(save_button)
        outer.addLayout(buttons)

        self._saved = self._values()
        self.resize(560, 720)

    def _make_display_group(self, config) -> QGroupBox:
        group = QGroupBox(tr("settings.group_display"))
        form = QFormLayout(group)

        # 言語の名前は、どの言語で表示していても読めるようにそれぞれの言語で書く
        self._language = QComboBox()
        for code, name in zip(LANGUAGES, (tr("settings.language_auto"), "日本語", "English")):
            self._language.addItem(name, code)
        self._language.setCurrentIndex(max(0, self._language.findData(config.language)))
        language_column = QVBoxLayout()
        language_column.addWidget(self._language, 0, Qt.AlignLeft)
        language_hint = QLabel(tr("settings.language_hint"))
        language_hint.setStyleSheet("color: gray;")
        language_hint.setWordWrap(True)
        language_column.addWidget(language_hint)
        form.addRow(tr("settings.language"), language_column)

        self._width = QSpinBox()
        self._width.setRange(*WIDTH_RANGE)
        self._width.setSingleStep(20)
        self._width.setSuffix(" px")
        self._width.setValue(config.width)
        self._width.valueChanged.connect(self._update_line_limit)
        form.addRow(tr("settings.width", default=DEFAULT_WIDTH), self._width)

        self._auto_limit = QCheckBox(tr("settings.auto_limit"))
        self._line_limit = QSpinBox()
        self._line_limit.setRange(*LINE_LIMIT_RANGE)
        self._line_limit.setSuffix(tr("settings.chars_suffix"))
        raw = _raw_line_limit()
        self._auto_limit.setChecked(raw is None)
        self._line_limit.setValue(raw if raw is not None else config.command_line_limit)
        self._auto_limit.toggled.connect(self._update_line_limit)
        row = QHBoxLayout()
        row.addWidget(self._auto_limit)
        row.addWidget(self._line_limit)
        row.addStretch(1)
        form.addRow(tr("settings.line_limit"), row)
        self._update_line_limit()

        self._delay_fixed = QRadioButton(tr("settings.delay_fixed"))
        self._delay_reading = QRadioButton(tr("settings.delay_reading"))
        mode_group = QButtonGroup(self)
        mode_group.addButton(self._delay_fixed)
        mode_group.addButton(self._delay_reading)
        (self._delay_reading if config.delay_mode == "reading" else self._delay_fixed).setChecked(True)
        self._delay_reading.toggled.connect(self._update_delay_widgets)
        mode_row = QHBoxLayout()
        mode_row.addWidget(self._delay_fixed)
        mode_row.addWidget(self._delay_reading)
        mode_row.addStretch(1)
        form.addRow(tr("settings.delay_mode"), mode_row)

        self._delay = QSpinBox()
        self._delay.setRange(*DELAY_RANGE)
        self._delay.setSuffix(tr("settings.seconds_suffix"))
        self._delay.setValue(config.delay_seconds)
        delay_row = QHBoxLayout()
        delay_row.addWidget(self._delay)
        self._delay_hint = QLabel()
        self._delay_hint.setStyleSheet("color: gray;")
        self._delay_hint.setWordWrap(True)
        delay_row.addWidget(self._delay_hint, 1)
        form.addRow(tr("settings.delay", default=DEFAULT_DELAY_SECONDS), delay_row)

        self._reading_cpm = QSpinBox()
        self._reading_cpm.setRange(*READING_CPM_RANGE)
        self._reading_cpm.setSingleStep(50)
        self._reading_cpm.setSuffix(tr("settings.cpm_suffix"))
        self._reading_cpm.setValue(config.reading_cpm)
        self._reading_cpm.valueChanged.connect(self._update_delay_widgets)
        cpm_row = QHBoxLayout()
        cpm_row.addWidget(self._reading_cpm)
        self._cpm_hint = QLabel()
        self._cpm_hint.setStyleSheet("color: gray;")
        self._cpm_hint.setWordWrap(True)
        cpm_row.addWidget(self._cpm_hint, 1)
        form.addRow(tr("settings.cpm", default=DEFAULT_READING_CPM), cpm_row)
        self._update_delay_widgets()
        return group

    def _update_delay_widgets(self, *_args) -> None:
        reading = self._delay_reading.isChecked()
        self._reading_cpm.setEnabled(reading)
        if reading:
            self._delay_hint.setText(tr("settings.delay_hint_reading"))
        else:
            self._delay_hint.setText(tr("settings.delay_hint_fixed"))
        example = -(-300 * 60 // self._reading_cpm.value())  # 切り上げ
        self._cpm_hint.setText(tr("settings.cpm_hint", example=example, max=READING_DELAY_MAX))

    def _make_sound_group(self, config) -> QGroupBox:
        group = QGroupBox(tr("settings.group_sound"))
        column = QVBoxLayout(group)
        self._sound_enabled = QCheckBox(tr("settings.sound_enabled"))
        self._sound_enabled.setChecked(config.sound_enabled)
        self._sound_enabled.toggled.connect(self._update_sound_widgets)
        column.addWidget(self._sound_enabled)

        self._sound_system_radio = QRadioButton(tr("settings.sound_system", dir=system_sound_dir()))
        self._sound_file_radio = QRadioButton(tr("settings.sound_file"))
        source_group = QButtonGroup(self)
        source_group.addButton(self._sound_system_radio)
        source_group.addButton(self._sound_file_radio)
        (self._sound_file_radio if config.sound_source == "file" else self._sound_system_radio).setChecked(True)
        source_group.buttonToggled.connect(self._update_sound_widgets)

        self._sound_system = QComboBox()
        names = list_system_sounds()
        if config.sound_system not in names:
            names.append(config.sound_system)  # 見つからない名前も選択状態を保つ
        self._sound_system.addItems(names)
        self._sound_system.setCurrentText(config.sound_system)
        row = QHBoxLayout()
        row.addWidget(self._sound_system_radio)
        row.addWidget(self._sound_system, 1)
        column.addLayout(row)

        self._sound_file = QLineEdit(config.sound_file)
        self._sound_file.setPlaceholderText(tr("settings.sound_file_placeholder"))
        self._sound_browse = QPushButton(tr("settings.browse"))
        self._sound_browse.clicked.connect(self._choose_sound_file)
        row = QHBoxLayout()
        row.addWidget(self._sound_file_radio)
        row.addWidget(self._sound_file, 1)
        row.addWidget(self._sound_browse)
        column.addLayout(row)

        preview = QPushButton(tr("settings.preview"))
        preview.clicked.connect(self._preview_sound)
        self._sound_preview = preview
        row = QHBoxLayout()
        row.addWidget(preview)
        hint = QLabel(tr("settings.sound_formats", formats=" ".join(SOUND_FILE_SUFFIXES)))
        hint.setStyleSheet("color: gray;")
        row.addWidget(hint, 1)
        column.addLayout(row)
        self._update_sound_widgets()
        return group

    def _update_sound_widgets(self, *_args) -> None:
        enabled = self._sound_enabled.isChecked()
        use_file = self._sound_file_radio.isChecked()
        for widget in (self._sound_system_radio, self._sound_file_radio, self._sound_preview):
            widget.setEnabled(enabled)
        self._sound_system.setEnabled(enabled and not use_file)
        self._sound_file.setEnabled(enabled and use_file)
        self._sound_browse.setEnabled(enabled and use_file)

    def _choose_sound_file(self) -> None:
        pattern = " ".join("*" + suffix for suffix in SOUND_FILE_SUFFIXES)
        path, _ = QFileDialog.getOpenFileName(
            self, tr("settings.choose_sound"), os.path.dirname(self._sound_file.text()) or os.path.expanduser("~"),
            tr("settings.sound_filter", pattern=pattern),
        )
        if path:
            self._sound_file.setText(path)

    def _selected_sound_path(self) -> str:
        if self._sound_file_radio.isChecked():
            return self._sound_file.text().strip()
        return system_sound_path(self._sound_system.currentText())

    def _preview_sound(self) -> None:
        path = self._selected_sound_path()
        if not os.path.isfile(path):
            QMessageBox.warning(
                self, tr("settings.preview_failed"),
                tr("settings.file_not_found", path=path or tr("settings.not_selected")),
            )
            return
        play_sound(path)

    def _make_scene_group(self, config) -> QGroupBox:
        group = QGroupBox(tr("settings.group_scenes"))
        inner = QWidget()
        column = QVBoxLayout(inner)
        self._scene_boxes: dict[str, QCheckBox] = {}
        current_group = None
        for scene in SCENES:
            if scene.group != current_group:
                current_group = scene.group
                heading = QLabel(tr(f"group.{current_group}"))
                heading.setStyleSheet("font-weight: bold; margin-top: 6px;")
                column.addWidget(heading)
            box = QCheckBox(tr(f"scene.{scene.key}.label"))
            box.setChecked(config.enabled(scene.key))
            box.setToolTip(scene.key)
            description = QLabel(tr(f"scene.{scene.key}.desc"))
            description.setWordWrap(True)
            description.setStyleSheet("color: gray; margin-left: 22px;")
            column.addWidget(box)
            column.addWidget(description)
            self._scene_boxes[scene.key] = box
        column.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setWidget(inner)
        layout = QVBoxLayout(group)
        layout.addWidget(scroll)
        return group

    def _update_line_limit(self, *_args) -> None:
        auto = self._auto_limit.isChecked()
        self._line_limit.setEnabled(not auto)
        if auto:
            self._line_limit.setValue(auto_line_limit(self._width.value()))

    def _values(self) -> dict:
        return {
            "language": self._language.currentData(),
            "width": self._width.value(),
            "command_line_limit": None if self._auto_limit.isChecked() else self._line_limit.value(),
            "delay_seconds": self._delay.value(),
            "delay_mode": "reading" if self._delay_reading.isChecked() else "fixed",
            "reading_cpm": self._reading_cpm.value(),
            "notify": {key: box.isChecked() for key, box in self._scene_boxes.items()},
            "sound": {
                "enabled": self._sound_enabled.isChecked(),
                "source": "file" if self._sound_file_radio.isChecked() else "system",
                "system": self._sound_system.currentText(),
                "file": self._sound_file.text().strip(),
            },
        }

    def _save(self) -> bool:
        values = self._values()
        sound = values["sound"]
        if sound["enabled"] and sound["source"] == "file" and not os.path.isfile(sound["file"]):
            QMessageBox.warning(self, tr("settings.save_failed"), tr("settings.sound_file_missing"))
            return False
        try:
            save_config(values)
        except OSError as error:
            QMessageBox.warning(self, tr("settings.save_failed"), str(error))
            return False
        self._saved = values
        self._status.setText(tr("settings.saved"))
        return True

    def _show_test(self) -> None:
        if not self._save():
            return
        subprocess.Popen(
            [
                sys.executable, NOTIFY_WINDOW_SCRIPT,
                "--title", message_title("title.test"),
                "--body", tr("body.test", width=self._width.value()),
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            **popen_flags(detach=True),
        )

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt override)
        if self._values() != self._saved:
            answer = QMessageBox.question(
                self,
                tr("settings.unsaved_title"),
                tr("settings.unsaved"),
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                QMessageBox.Save,
            )
            if answer == QMessageBox.Cancel or (answer == QMessageBox.Save and not self._save()):
                event.ignore()
                return
        event.accept()


def _raw_line_limit() -> int | None:
    """config.json に書かれた command_line_limit（自動なら None）。Config は自動計算後の値しか持たないため読み直す。"""
    import json

    from hooknotice_config import CONFIG_PATH

    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            value = json.load(f).get("command_line_limit")
    except (OSError, ValueError, AttributeError):
        return None
    low, high = LINE_LIMIT_RANGE
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        return None
    return value


def main() -> int:
    use_utf8_stdio()
    if "--detach" in sys.argv[1:]:
        # /hooknotice-settings から呼ばれたとき。自分を切り離して起動し直し、呼び出し元をすぐ戻す
        subprocess.Popen(
            [sys.executable, os.path.abspath(__file__)],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            **popen_flags(detach=True),
        )
        return 0
    app = QApplication(sys.argv[:1])
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    lock = QLockFile(str(LOCK_PATH))
    lock.setStaleLockTime(0)  # 異常終了したプロセスのロックは pid の生存確認で取り戻す
    if not lock.tryLock(0):
        return 0  # すでに開いている
    window = SettingsWindow()
    window.setWindowFlag(Qt.WindowStaysOnTopHint, True)
    window.show()
    window.raise_()
    window.activateWindow()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
