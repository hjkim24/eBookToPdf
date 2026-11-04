"""YES24 eBook 화면을 페이지마다 캡처해 PDF로 저장하는 도구 (macOS / Windows).

설치: pip3 install PySide6 img2pdf
실행: python3 eBookToPdf_v2.py
macOS는 처음 실행 시 터미널 앱에 '화면 기록'과 '손쉬운 사용' 권한을 허용해야 한다.
"""
import ctypes
import logging
import os
import subprocess
import sys
import tempfile
import time

import img2pdf
from PySide6.QtCore import QRect, Qt, QThread, Signal
from PySide6.QtGui import QColor, QCursor, QGuiApplication, QPainter, QPen
from PySide6.QtWidgets import (QApplication, QFileDialog, QFormLayout, QHBoxLayout, QLabel,
                               QPushButton, QSlider, QSpinBox, QWidget)

logging.getLogger('img2pdf').setLevel(logging.ERROR)  # 페이지마다 뜨는 알파 채널 경고 숨김

if sys.platform == 'darwin':
    VIEWER_APP = 'YES24_eBook'
    KEY_RIGHT = 124  # macOS 가상 키코드 (오른쪽 방향키)

    _cg = ctypes.CDLL('/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics')
    _cg.CGPreflightScreenCaptureAccess.restype = ctypes.c_bool
    _cg.CGRequestScreenCaptureAccess.restype = ctypes.c_bool
    _cg.CGEventCreateKeyboardEvent.restype = ctypes.c_void_p
    _cg.CGEventCreateKeyboardEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint16, ctypes.c_bool]
    _cg.CGEventPost.argtypes = [ctypes.c_uint32, ctypes.c_void_p]
    _cf = ctypes.CDLL('/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation')
    _cf.CFRelease.argtypes = [ctypes.c_void_p]
    _ax = ctypes.CDLL('/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices')
    _ax.AXIsProcessTrusted.restype = ctypes.c_bool

    def focus_viewer(_region):
        subprocess.run(['open', '-a', VIEWER_APP], check=True)

    def grab(r, path):
        # screencapture는 포인트 좌표를 받고 Retina 원본 해상도로 저장한다
        subprocess.run(['screencapture', '-x', '-R', f'{r.x()},{r.y()},{r.width()},{r.height()}', path],
                       check=True)

    def press_right():
        for key_down in (True, False):
            event = _cg.CGEventCreateKeyboardEvent(None, KEY_RIGHT, key_down)
            _cg.CGEventPost(0, event)  # kCGHIDEventTap: 맨 앞 앱으로 전달
            _cf.CFRelease(event)

    def missing_permissions():
        # 권한이 없으면 screencapture는 배경화면만 찍고 키 입력은 조용히 무시되므로 미리 막는다
        missing = []
        if not _cg.CGPreflightScreenCaptureAccess():
            _cg.CGRequestScreenCaptureAccess()
            missing.append('화면 기록')
        if not _ax.AXIsProcessTrusted():
            subprocess.run(['open', 'x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility'])
            missing.append('손쉬운 사용')
        return missing

else:  # Windows. Qt6가 DPI 인식 모드로 띄우므로 아래 API는 모두 물리 픽셀 좌표를 쓴다
    from PIL import ImageGrab  # img2pdf 의존성으로 함께 설치됨

    _user32 = ctypes.windll.user32
    VK_RIGHT, KEYEVENTF_EXTENDEDKEY, KEYEVENTF_KEYUP = 0x27, 0x1, 0x2
    MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP = 0x2, 0x4

    def focus_viewer(r):
        # 뷰어 창 이름에 기대지 않도록 기존 버전처럼 캡처 영역 좌상단을 한 번 클릭해 포커스를 준다
        _user32.SetCursorPos(r.x(), r.y())
        _user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        _user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)

    def grab(r, path):
        ImageGrab.grab(bbox=(r.x(), r.y(), r.right() + 1, r.bottom() + 1), all_screens=True).save(path)

    def press_right():
        # 방향키는 확장 키 플래그가 없으면 숫자패드 6으로 해석될 수 있다
        _user32.keybd_event(VK_RIGHT, 0, KEYEVENTF_EXTENDEDKEY, 0)
        _user32.keybd_event(VK_RIGHT, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)

    def missing_permissions():
        return []


def to_native(r, screen):
    """Qt 논리 좌표를 캡처용 좌표로 바꾼다. macOS는 포인트 그대로, Windows는 배율을 곱한 물리 픽셀."""
    if sys.platform == 'darwin':
        return r
    # Qt6는 화면 원점은 물리 좌표 그대로 두고 크기만 배율로 나눠 쓴다
    origin, dpr = screen.geometry().topLeft(), screen.devicePixelRatio()
    return QRect(origin + (r.topLeft() - origin) * dpr, r.size() * dpr)


class RegionSelector(QWidget):
    """화면 전체를 덮는 반투명 막. 드래그한 사각형을 전역 좌표로 돌려준다."""
    selected = Signal(QRect)

    def __init__(self):
        super().__init__(None, Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
                         | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(Qt.CursorShape.CrossCursor)
        screen = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
        self.setGeometry(screen.geometry())
        self.target_screen = screen
        self.origin = self.current = None

    def drag_rect(self):
        return QRect(self.origin, self.current).normalized()

    def paintEvent(self, _):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(0, 0, 0, 90))
        if self.origin:
            p.fillRect(self.drag_rect(), QColor(255, 255, 255, 40))
            p.setPen(QPen(QColor(255, 59, 48), 2))
            p.drawRect(self.drag_rect())

    def mousePressEvent(self, e):
        self.origin = self.current = e.position().toPoint()

    def mouseMoveEvent(self, e):
        self.current = e.position().toPoint()
        self.update()

    def mouseReleaseEvent(self, e):
        self.current = e.position().toPoint()
        r = self.drag_rect()
        self.close()
        if r.width() > 10 and r.height() > 10:
            self.selected.emit(to_native(r.translated(self.geometry().topLeft()), self.target_screen))

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Escape:
            self.close()


class CaptureWorker(QThread):
    progress = Signal(str)
    done = Signal(str)

    def __init__(self, region, pages, delay, out_path):
        super().__init__()
        self.region, self.pages, self.delay, self.out_path = region, pages, delay, out_path
        self.stopped = False

    def run(self):
        try:
            self.done.emit(self.capture())
        except Exception as e:
            self.done.emit(f'오류: {e}')

    def capture(self):
        focus_viewer(self.region)
        time.sleep(1)  # 뷰어가 맨 앞으로 올라올 때까지
        with tempfile.TemporaryDirectory() as tmp:
            images = []
            for i in range(1, self.pages + 1):
                if self.stopped:
                    break
                path = os.path.join(tmp, f'{i:05}.png')
                grab(self.region, path)
                images.append(path)
                self.progress.emit(f'{i}/{self.pages} 캡처 중')
                if i < self.pages:
                    press_right()
                    time.sleep(self.delay)
            if not images:
                return '캡처한 페이지가 없습니다.'
            self.progress.emit(f'PDF 변환 중 ({len(images)}페이지)')
            with open(self.out_path, 'wb') as f:
                f.write(img2pdf.convert(images))
        return f'완료: {os.path.basename(self.out_path)} ({len(images)}페이지)'


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('eBookToPdf')
        self.region = None
        self.selector = None
        self.worker = None

        self.region_label = QLabel('미지정')
        select_btn = QPushButton('드래그로 지정')
        select_btn.clicked.connect(self.select_region)
        region_row = QHBoxLayout()
        region_row.addWidget(self.region_label, 1)
        region_row.addWidget(select_btn)

        self.pages = QSpinBox()
        self.pages.setRange(1, 9999)
        self.pages.setValue(100)

        self.speed_label = QLabel()
        self.speed = QSlider(Qt.Orientation.Horizontal)
        self.speed.setRange(1, 20)  # 0.1 ~ 2.0초
        self.speed.valueChanged.connect(lambda v: self.speed_label.setText(f'캡처 간격 {v / 10:.1f}초'))
        self.speed.setValue(5)

        self.start_btn = QPushButton('PDF로 만들기')
        self.start_btn.setMinimumHeight(44)
        self.start_btn.clicked.connect(self.start_or_stop)
        self.status = QLabel('')
        self.status.setWordWrap(True)

        form = QFormLayout(self)
        form.addRow('캡처 영역', region_row)
        form.addRow('총 페이지 수', self.pages)
        form.addRow(self.speed_label, self.speed)
        form.addRow(self.start_btn)
        form.addRow(self.status)
        self.setFixedWidth(420)

    def select_region(self):
        self.selector = RegionSelector()
        self.selector.selected.connect(self.set_region)
        self.selector.show()
        self.selector.raise_()
        self.selector.activateWindow()

    def set_region(self, r):
        self.region = r
        self.region_label.setText(f'({r.x()}, {r.y()})  {r.width()} × {r.height()}')

    def start_or_stop(self):
        if self.worker and self.worker.isRunning():
            self.worker.stopped = True
            self.status.setText('중지하는 중… 지금까지 찍은 페이지로 PDF를 만듭니다.')
            return
        if not self.region:
            self.status.setText('먼저 캡처 영역을 드래그로 지정하세요.')
            return
        missing = missing_permissions()
        if missing:
            self.status.setText(f'시스템 설정에서 터미널 앱에 {", ".join(missing)} 권한을 허용한 뒤 터미널을 재시작하세요.')
            return
        path, _ = QFileDialog.getSaveFileName(self, 'PDF 저장', os.path.expanduser('~/Downloads/ebook.pdf'),
                                              'PDF (*.pdf)')
        if not path:
            return
        if not path.lower().endswith('.pdf'):
            path += '.pdf'
        self.worker = CaptureWorker(self.region, self.pages.value(), self.speed.value() / 10, path)
        self.worker.progress.connect(self.status.setText)
        self.worker.done.connect(self.finish)
        self.start_btn.setText('중지')
        self.worker.start()

    def finish(self, message):
        self.status.setText(message)
        self.start_btn.setText('PDF로 만들기')


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
