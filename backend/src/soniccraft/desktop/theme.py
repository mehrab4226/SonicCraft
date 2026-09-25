"""Shared studio palette, vector icons and lightweight presentation helpers."""
from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import QColor, QFont, QIcon, QPainter, QPen, QPixmap, QPolygonF
from PyQt6.QtWidgets import QFrame, QLabel, QVBoxLayout, QSizePolicy

BACKGROUND = "#0d1115"
ACCENT = "#91efd0"

STYLESHEET = """
QWidget { font-family: 'Segoe UI'; font-size: 12px; color: #e8edf1; }
QMainWindow, QWidget#workspace { background: #0d1115; }
QMenuBar { background: #0d1115; color: #9ba8b3; padding: 4px 16px; }
QMenuBar::item { padding: 5px 12px; background: transparent; }
QMenuBar::item:selected, QMenu::item:selected { background: #273b36; color: #91efd0; }
QMenu { background: #191f25; border: 1px solid #34414b; padding: 6px; }
QMenu::item { padding: 8px 28px; }
QToolBar { background: #13191f; border: 0; border-bottom: 1px solid #293139; spacing: 7px; padding: 10px 20px; }
QToolBar::separator { background: #303940; width: 1px; margin: 4px 9px; }
QToolButton, QPushButton { background: #202931; border: 1px solid #34414b; border-radius: 6px; padding: 8px 13px; font-weight: 600; }
QToolButton:hover, QPushButton:hover { background: #2c3a41; border-color: #718e8b; }
QToolButton:pressed, QPushButton:pressed { background: #354e47; }
QToolButton:checked { background: #263f38; border-color: #91efd0; color: #91efd0; }
QToolButton:disabled, QPushButton:disabled { background: #181f25; color: #66737e; border-color: #283139; }
QPushButton[primary="true"], QToolButton#playButton { background: #91efd0; color: #10271f; border-color: #91efd0; }
QPushButton[primary="true"]:hover, QToolButton#playButton:hover { background: #b2ffe4; }
QPushButton[primary="true"]:disabled, QToolButton#playButton:disabled { background: #253d35; color: #7b998e; border-color: #314b42; }
QPushButton[danger="true"] { color: #ffaca6; }
QPushButton:focus, QToolButton:focus, QComboBox:focus, QDoubleSpinBox:focus, QSpinBox:focus { border: 1px solid #91efd0; }
QLabel { background: transparent; }
QLabel#brand { font-size: 23px; font-weight: 700; letter-spacing: -1px; }
QLabel#eyebrow { color: #91efd0; font-size: 10px; font-weight: 700; letter-spacing: 2px; }
QLabel#muted { color: #94a2ad; }
QLabel#sectionTitle { font-size: 15px; font-weight: 600; }
QLabel#fileTitle { font-size: 22px; font-weight: 600; }
QLabel#heroTitle { font-size: 27px; font-weight: 600; letter-spacing: -1px; }
QLabel#timecode { font-family: 'Consolas'; font-size: 24px; color: #dceae4; padding: 0 14px; }
QLabel#badge { color: #91efd0; background: #20352d; border: 1px solid #345146; border-radius: 5px; padding: 5px 9px; font-size: 10px; font-weight: 600; }
QLabel#metricValue { font-family: 'Consolas'; font-size: 19px; color: #e0ece8; }
QFrame#panel, QFrame#metric { background: #151c22; border: 1px solid #2b353e; border-radius: 9px; }
QFrame#sidebar { background: #151c22; border: 1px solid #2b353e; border-radius: 9px; }
QPushButton#categoryButton { text-align: left; padding: 14px 12px; font-weight: 500; line-height: 1.6; background: #1a252c; }
QPushButton#categoryButton:hover { background: #263d35; border-color: #91efd0; }
QFrame#effectCard { background: #192229; border: 1px solid #303c45; border-radius: 8px; }
QFrame#emptyState { background: #111b20; border: 1px dashed #3a5953; border-radius: 9px; }
QFrame#selectionPanel { background: #192329; border: 0; border-radius: 7px; }
QComboBox, QDoubleSpinBox, QSpinBox { background: #10171c; border: 1px solid #3a4853; border-radius: 5px; padding: 7px 9px; min-height: 18px; selection-background-color: #355e50; }
QComboBox { padding-right: 24px; }
QComboBox::drop-down { border: 0; width: 23px; }
QComboBox QAbstractItemView { background: #202a32; selection-background-color: #345448; padding: 5px; }
QComboBox:disabled, QDoubleSpinBox:disabled, QSpinBox:disabled { color: #697983; border-color: #28363e; }
QTabWidget::pane { border: 0; background: #151c22; }
QTabBar::tab { background: transparent; color: #94a2ad; padding: 12px 21px; border-bottom: 2px solid transparent; font-weight: 600; }
QTabBar::tab:selected { color: #91efd0; border-bottom: 2px solid #91efd0; background: #1b2a29; }
QTabBar::tab:hover { color: #e8edf1; background: #222e35; }
QTabBar::tab:focus { border-top: 1px solid #91efd0; }
QScrollArea, QScrollArea > QWidget > QWidget { border: 0; background: #151c22; }
QScrollBar:vertical { background: #141c22; width: 8px; margin: 0; }
QScrollBar::handle:vertical { background: #42534f; border-radius: 4px; min-height: 24px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { background: #141c22; height: 8px; margin: 0; }
QScrollBar::handle:horizontal { background: #42534f; border-radius: 4px; min-width: 24px; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QSlider::groove:vertical { width: 4px; background: #0d1419; border-radius: 2px; }
QSlider::handle:vertical { background: #91efd0; height: 12px; margin: 0 -6px; border-radius: 3px; }
QSlider::sub-page:vertical { background: #3d6b5a; }
QSlider::handle:vertical:disabled { background: #566a64; }
QSlider::handle:vertical:focus { border: 2px solid #ffffff; }
QSlider::groove:horizontal { height: 4px; background: #0d1419; border-radius: 2px; }
QSlider::handle:horizontal { background: #91efd0; width: 10px; margin: -5px 0; border-radius: 3px; }
QSlider::sub-page:horizontal { background: #3d6b5a; }
QSlider::handle:horizontal:disabled { background: #566a64; }
QSplitter::handle { background: #0d1115; height: 10px; }
QSplitter::handle:hover { background: #344d44; }
QStatusBar { background: #11181d; color: #94a2ad; border-top: 1px solid #29343b; padding: 4px 12px; }
QStatusBar::item { border: 0; }
QProgressBar { background: #26372f; border: 0; border-radius: 2px; max-height: 3px; }
QProgressBar::chunk { background: #91efd0; }
QDockWidget { font-weight: 600; }
QDockWidget::title { background: #1b272e; padding: 9px; }
QToolTip { background: #263630; color: #e8fff4; border: 1px solid #527868; padding: 6px; }
"""


def label(text, name="muted"):
    widget = QLabel(text)
    widget.setObjectName(name)
    widget.setTextFormat(Qt.TextFormat.PlainText)
    return widget


class FileTitle(QLabel):
    """Keep long filenames from forcing the editor beyond the screen width."""
    def __init__(self, text):
        super().__init__(text)
        self.setObjectName("fileTitle")
        self.setTextFormat(Qt.TextFormat.PlainText)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setFont(self.font())
        painter.setPen(self.palette().windowText().color())
        text = self.fontMetrics().elidedText(self.text(), Qt.TextElideMode.ElideMiddle, self.width())
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, text)


def card(title, subtitle=None):
    frame = QFrame()
    frame.setObjectName("effectCard")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(16, 12, 16, 12)
    layout.setSpacing(8)
    layout.addWidget(label(title, "sectionTitle"))
    if subtitle:
        hint = label(subtitle)
        hint.setWordWrap(True)
        layout.addWidget(hint)
    return frame, layout


def icon(name, color="#c9d7d4"):
    """Draw resolution-independent monochrome controls, without asset dependencies."""
    pixmap = QPixmap(48, 48)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.scale(2, 2)
    painter.setPen(QPen(QColor(color), 1.7, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    if name in ("brand", "spectrum"):
        for x, height in ((4, 5), (8, 12), (12, 19), (16, 10), (20, 5)):
            painter.drawLine(QPointF(x, 12-height/2), QPointF(x, 12+height/2))
    elif name == "play":
        painter.setBrush(QColor(color))
        painter.drawPolygon(QPolygonF([QPointF(8, 5), QPointF(19, 12), QPointF(8, 19)]))
    elif name == "pause":
        painter.drawLine(8, 5, 8, 19)
        painter.drawLine(16, 5, 16, 19)
    elif name == "stop":
        painter.drawRoundedRect(QRectF(6, 6, 12, 12), 1, 1)
    elif name == "open":
        painter.drawPolyline(QPolygonF([QPointF(3, 18), QPointF(3, 6), QPointF(9, 6), QPointF(12, 9), QPointF(21, 9)]))
        painter.drawPolygon(QPolygonF([QPointF(3, 18), QPointF(6, 11), QPointF(22, 11), QPointF(19, 18)]))
    elif name == "save":
        painter.drawLine(12, 3, 12, 15)
        painter.drawPolyline(QPolygonF([QPointF(8, 7), QPointF(12, 3), QPointF(16, 7)]))
        painter.drawPolyline(QPolygonF([QPointF(4, 14), QPointF(4, 20), QPointF(20, 20), QPointF(20, 14)]))
    elif name in ("undo", "redo"):
        if name == "redo":
            painter.translate(24, 0)
            painter.scale(-1, 1)
        painter.drawArc(QRectF(6, 7, 14, 13), -40 * 16, 235 * 16)
        painter.drawPolyline(QPolygonF([QPointF(4, 5), QPointF(4, 11), QPointF(10, 11)]))
    else:
        painter.drawRoundedRect(QRectF(4, 5, 16, 14), 2, 2)
        painter.drawLine(8, 12, 16, 12)
    painter.end()
    return QIcon(pixmap)


def style_plot(plot):
    plot_item = plot.getPlotItem() if hasattr(plot, "getPlotItem") else plot
    if hasattr(plot, "setBackground"):
        plot.setBackground(BACKGROUND)
    else:
        plot.getViewBox().setBackgroundColor(BACKGROUND)
    plot_item.showGrid(x=True, y=True, alpha=0.1)
    for edge in ("left", "bottom"):
        axis = plot_item.getAxis(edge)
        axis.setPen("#34434a")
        axis.setTextPen("#899ba5")
        axis.setStyle(tickFont=QFont("Consolas", 9))
    plot_item.hideButtons()
