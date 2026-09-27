"""Shared studio palette, vector icons and lightweight presentation helpers."""
from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import QColor, QFont, QIcon, QPainter, QPen, QPixmap, QPolygonF
from PyQt6.QtWidgets import QFrame, QLabel, QVBoxLayout, QSizePolicy

BACKGROUND = "#141416"
ACCENT = "#e6bd78"

STYLESHEET = """
QWidget { font-family: 'Segoe UI'; font-size: 12px; color: #e8edf1; }
QMainWindow, QWidget#workspace { background: #141416; }
QMenuBar { background: #141416; color: #9ba8b3; padding: 1px 12px; }
QMenuBar::item { padding: 3px 10px; background: transparent; }
QMenuBar::item:selected, QMenu::item:selected { background: #44392d; color: #e6bd78; }
QMenu { background: #191f25; border: 1px solid #34414b; padding: 6px; }
QMenu::item { padding: 8px 28px; }
QToolBar { background: #1b1b1e; border: 0; border-bottom: 1px solid #293139; spacing: 7px; padding: 5px 12px; }
QToolBar::separator { background: #303940; width: 1px; margin: 4px 9px; }
QToolButton, QPushButton { background: #2c2c31; border: 1px solid #34414b; border-radius: 6px; padding: 6px 10px; font-weight: 600; }
QToolButton:hover, QPushButton:hover { background: #3a3732; border-color: #9d896a; }
QToolButton:pressed, QPushButton:pressed { background: #554533; }
QToolButton:checked { background: #423728; border-color: #e6bd78; color: #e6bd78; }
QToolButton:disabled, QPushButton:disabled { background: #181f25; color: #66737e; border-color: #283139; }
QPushButton[primary="true"], QToolButton#playButton { background: #e6bd78; color: #292116; border-color: #e6bd78; }
QPushButton[primary="true"]:hover, QToolButton#playButton:hover { background: #f4d7a4; }
QPushButton[primary="true"]:disabled, QToolButton#playButton:disabled { background: #3a332a; color: #a39580; border-color: #4b4133; }
QPushButton[danger="true"] { color: #ffaca6; }
QPushButton:focus, QToolButton:focus, QComboBox:focus, QDoubleSpinBox:focus, QSpinBox:focus { border: 1px solid #e6bd78; }
QLabel { background: transparent; }
QLabel#brand { font-size: 19px; font-weight: 700; letter-spacing: -1px; }
QLabel#eyebrow { color: #e6bd78; font-size: 10px; font-weight: 700; letter-spacing: 2px; }
QLabel#muted { color: #94a2ad; }
QLabel#sectionTitle { font-size: 15px; font-weight: 600; }
QLabel#fileTitle { font-size: 18px; font-weight: 600; }
QLabel#heroTitle { font-size: 27px; font-weight: 600; letter-spacing: -1px; }
QLabel#timecode { font-family: 'Consolas'; font-size: 20px; color: #eee5d7; padding: 0 14px; }
QLabel#badge { color: #e6bd78; background: #352e25; border: 1px solid #514430; border-radius: 5px; padding: 5px 9px; font-size: 10px; font-weight: 600; }
QLabel#metricValue { font-family: 'Consolas'; font-size: 14px; color: #eee5d7; }
QFrame#panel, QFrame#metric { background: #1d1d21; border: 1px solid #2b353e; border-radius: 9px; }
QFrame#sidebar { background: #1d1d21; border: 1px solid #2b353e; border-radius: 9px; }
QPushButton#categoryButton { text-align: left; padding: 14px 12px; font-weight: 500; line-height: 1.6; background: #26262b; }
QPushButton#categoryButton:hover { background: #40372a; border-color: #e6bd78; }
QFrame#effectCard { background: #242428; border: 1px solid #303c45; border-radius: 8px; }
QFrame#emptyState { background: #1a191c; border: 1px dashed #62513c; border-radius: 9px; }
QFrame#selectionPanel { background: #252429; border: 0; border-radius: 7px; }
QComboBox, QDoubleSpinBox, QSpinBox { background: #18181b; border: 1px solid #3a4853; border-radius: 5px; padding: 7px 9px; min-height: 18px; selection-background-color: #5e4c35; }
QComboBox { padding-right: 24px; }
QComboBox::drop-down { border: 0; width: 23px; }
QComboBox QAbstractItemView { background: #202a32; selection-background-color: #54452f; padding: 5px; }
QComboBox:disabled, QDoubleSpinBox:disabled, QSpinBox:disabled { color: #697983; border-color: #28363e; }
QTabWidget::pane { border: 0; background: #1d1d21; }
QTabBar::tab { background: transparent; color: #94a2ad; padding: 12px 21px; border-bottom: 2px solid transparent; font-weight: 600; }
QTabBar::tab:selected { color: #e6bd78; border-bottom: 2px solid #e6bd78; background: #332d25; }
QTabBar::tab:hover { color: #e8edf1; background: #222e35; }
QTabBar::tab:focus { border-top: 1px solid #e6bd78; }
QScrollArea, QScrollArea > QWidget > QWidget { border: 0; background: #1d1d21; }
QScrollBar:vertical { background: #141c22; width: 8px; margin: 0; }
QScrollBar::handle:vertical { background: #5b5145; border-radius: 4px; min-height: 24px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { background: #141c22; height: 8px; margin: 0; }
QScrollBar::handle:horizontal { background: #5b5145; border-radius: 4px; min-width: 24px; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QSlider::groove:vertical { width: 4px; background: #0d1419; border-radius: 2px; }
QSlider::handle:vertical { background: #e6bd78; height: 12px; margin: 0 -6px; border-radius: 3px; }
QSlider::sub-page:vertical { background: #806747; }
QSlider::handle:vertical:disabled { background: #6a6050; }
QSlider::handle:vertical:focus { border: 2px solid #ffffff; }
QSlider::groove:horizontal { height: 4px; background: #0d1419; border-radius: 2px; }
QSlider::handle:horizontal { background: #e6bd78; width: 10px; margin: -5px 0; border-radius: 3px; }
QSlider::sub-page:horizontal { background: #806747; }
QSlider::handle:horizontal:disabled { background: #6a6050; }
QSplitter::handle { background: #141416; height: 10px; }
QSplitter::handle:hover { background: #554735; }
QStatusBar { background: #11181d; color: #94a2ad; border-top: 1px solid #29343b; padding: 4px 12px; }
QStatusBar::item { border: 0; }
QProgressBar { background: #393027; border: 0; border-radius: 2px; max-height: 3px; }
QProgressBar::chunk { background: #e6bd78; }
QDockWidget { font-weight: 600; }
QDockWidget::title { background: #1b272e; padding: 9px; }
QToolTip { background: #383026; color: #fff1d9; border: 1px solid #8a724c; padding: 6px; }
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


def icon(name, color="#ddd6ca"):
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
    # Gestures must never pan/zoom a graph or change its unit prefix.
    plot_item.setMouseEnabled(x=False, y=False)
    plot_item.setMenuEnabled(False)
    for edge in ("left", "bottom"):
        plot_item.getAxis(edge).enableAutoSIPrefix(False)
