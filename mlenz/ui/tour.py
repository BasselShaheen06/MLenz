"""
mlenz.ui.tour
~~~~~~~~~~~~~~~~~
Interactive overlay tour with spotlight and prompts.
"""

from __future__ import annotations

from dataclasses import dataclass

from PyQt5.QtCore import Qt, QRect, QRectF, QPoint
from PyQt5.QtGui import QColor, QPainter, QPainterPath, QFont
from PyQt5.QtWidgets import (
    QFrame,
    QLabel,
    QPushButton,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
)

from mlenz.ui.theme import ThemeManager

_theme = ThemeManager()


@dataclass(frozen=True)
class TourStep:
    widget: QWidget | None
    title: str
    body: str


class TourOverlay(QWidget):
    """Full-window overlay that highlights UI elements step by step."""

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setVisible(False)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAutoFillBackground(False)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)

        self._steps: list[TourStep] = []
        self._index = 0
        self._target_rect = QRect()

        self._panel = QFrame(self)
        self._panel.setObjectName("tourPanel")
        self._panel.setStyleSheet(self._panel_style())
        self._panel_lay = QVBoxLayout(self._panel)
        self._panel_lay.setContentsMargins(14, 12, 14, 12)
        self._panel_lay.setSpacing(8)

        self._title = QLabel("")
        self._title.setStyleSheet("color:#E0F2F1; font-size:14px; font-weight:700;")
        self._title.setWordWrap(True)
        self._panel_lay.addWidget(self._title)

        self._body = QLabel("")
        self._body.setStyleSheet("color:#B2DFDB; font-size:12px;")
        self._body.setWordWrap(True)
        self._panel_lay.addWidget(self._body)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        self._back_btn = QPushButton("Back")
        self._next_btn = QPushButton("Next")
        self._skip_btn = QPushButton("Skip")
        for btn in (self._back_btn, self._next_btn, self._skip_btn):
            btn.setFixedHeight(26)
            btn.setStyleSheet(self._button_style())
        btn_row.addWidget(self._back_btn)
        btn_row.addWidget(self._next_btn)
        btn_row.addStretch()
        btn_row.addWidget(self._skip_btn)
        self._panel_lay.addLayout(btn_row)

        self._back_btn.clicked.connect(self._prev)
        self._next_btn.clicked.connect(self._next)
        self._skip_btn.clicked.connect(self.stop)

    def start(self, steps: list[TourStep]) -> None:
        if not steps:
            return
        self._steps = steps
        self._index = 0
        self._apply_step()
        self.setVisible(True)
        self.raise_()
        self.setFocus(Qt.ActiveWindowFocusReason)

    def stop(self) -> None:
        self.setVisible(False)
        self._steps = []
        self._index = 0
        self._target_rect = QRect()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_step_position()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        hole = None
        if not self._target_rect.isNull():
            hole = QRectF(self._target_rect.adjusted(-6, -6, 6, 6))

        mask = QPainterPath()
        mask.addRect(QRectF(self.rect()))
        if hole is not None:
            mask.addRoundedRect(hole, 6.0, 6.0)
            mask.setFillRule(Qt.OddEvenFill)

        painter.fillPath(mask, QColor(0, 0, 0, 180))

        if hole is not None:
            painter.setPen(QColor(255, 255, 255, 160))
            painter.drawRoundedRect(hole, 6.0, 6.0)

    def _apply_step(self) -> None:
        step = self._steps[self._index]
        self._title.setText(step.title)
        self._body.setText(step.body)

        self._back_btn.setEnabled(self._index > 0)
        if self._index == len(self._steps) - 1:
            self._next_btn.setText("Finish")
        else:
            self._next_btn.setText("Next")

        self._target_rect = self._calc_target_rect(step.widget)
        self._apply_step_position()
        self.update()

    def _apply_step_position(self) -> None:
        if self._target_rect.isNull():
            self._panel.move(20, 20)
            return
        pad = 12
        panel_size = self._panel.sizeHint()
        right = self._target_rect.right() + pad
        below = self._target_rect.bottom() + pad
        candidates = []
        if right + panel_size.width() < self.width():
            candidates.append(QPoint(right, max(pad, self._target_rect.top())))
        if below + panel_size.height() < self.height():
            candidates.append(QPoint(max(pad, self._target_rect.left()), below))
        candidates.append(
            QPoint(
                max(pad, self.width() - panel_size.width() - pad),
                max(pad, self.height() - panel_size.height() - pad),
            )
        )

        panel_rect = QRect(QPoint(0, 0), panel_size)
        for pos in candidates:
            panel_rect.moveTopLeft(pos)
            if not panel_rect.intersects(self._target_rect):
                self._panel.move(self._clamp_pos(pos, panel_size))
                return

        self._panel.move(self._clamp_pos(candidates[-1], panel_size))

    def _clamp_pos(self, pos: QPoint, panel_size) -> QPoint:
        pad = 8
        max_x = max(pad, self.width() - panel_size.width() - pad)
        max_y = max(pad, self.height() - panel_size.height() - pad)
        x = min(max(pos.x(), pad), max_x)
        y = min(max(pos.y(), pad), max_y)
        return QPoint(x, y)

    def _calc_target_rect(self, widget: QWidget | None) -> QRect:
        if widget is None:
            return QRect()
        if not widget.isVisible():
            return QRect()
        top_left = widget.mapToGlobal(QPoint(0, 0))
        bottom_right = widget.mapToGlobal(QPoint(widget.width(), widget.height()))
        tl = self.mapFromGlobal(top_left)
        br = self.mapFromGlobal(bottom_right)
        return QRect(tl, br)

    def _next(self) -> None:
        if self._index >= len(self._steps) - 1:
            self.stop()
            return
        self._index += 1
        self._apply_step()

    def _prev(self) -> None:
        if self._index <= 0:
            return
        self._index -= 1
        self._apply_step()

    def _panel_style(self) -> str:
        return "QFrame#tourPanel { background: transparent; border: none; }"

    def _button_style(self) -> str:
        T = _theme.palette()
        return (
            "QPushButton {"
            f"background:{T['surface']}; color:{T['text']};"
            f"border:1px solid {T['border_med']}; border-radius:5px;"
            "font-size:11px; padding:0 10px;"
            "}"
            "QPushButton:hover {"
            f"border-color:{T['accent']}; color:{T['accent']};"
            "}"
        )
