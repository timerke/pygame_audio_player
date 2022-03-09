import datetime
import os
import sys
import pygame
import pygame._sdl2 as sdl2
from epsound import WavPlayer
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Qt, QThread, QTimer
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (QApplication, QComboBox, QFormLayout, QGridLayout, QGroupBox, QLabel, QLineEdit,
                             QMainWindow, QPushButton, QTextEdit, QVBoxLayout, QWidget)


class ThreadForPlayer(QThread):
    """
    Class for thread to play sounds.
    """

    sound_played = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._index: int = 0
        self._wav_player: WavPlayer = WavPlayer()
        self._sound_names: list = []
        self._dir_name: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audio")
        for index, file_name in enumerate(sorted(os.listdir(self._dir_name))):
            self._sound_names.append(file_name)
            self._wav_player.add_sound(os.path.join(self._dir_name, file_name), file_name)
        pygame.init()
        self.audio_devices: list = sdl2.get_audio_device_names()
        print(f"Available audio devices: {self.audio_devices}")
        pygame.mixer.init()

    @pyqtSlot()
    def play_next_sound(self):
        """
        Slot plays next sound from list.
        """

        if self._index >= len(self._sound_names):
            self._index = 0
        sound_name = self._sound_names[self._index]
        self._index += 1
        self.sound_played.emit(sound_name)
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audio", sound_name)
        sound = pygame.mixer.Sound(path)
        sound.play()
        # self._wav_player.play(sound_name)

    @pyqtSlot(str)
    def play_sound(self, sound_name: str):
        """
        Slot plays sound with given name.
        :param sound_name: name of sound to play.
        """

        self.sound_played.emit(sound_name)
        self._wav_player.play(sound_name)


class MainWindow(QMainWindow):
    """
    Class with main window of application.
    """

    certain_sound_required = pyqtSignal(str)
    sounds_required = pyqtSignal()

    def __init__(self, audio_devices: list):
        """
        :param audio_devices: list of available audio devices.
        """

        super().__init__()
        self.audio_devices: list = audio_devices
        self.dir_name: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audio")
        self.timer = QTimer()
        self.timer.timeout.connect(self.sounds_required.emit)
        self.timer.setInterval(100)
        self.timer.setSingleShot(False)
        self._init_ui()

    def _enable_widgets(self, status: bool = True):
        """
        Method enables or disables some widgets.
        :param status: if True widgets will be enabled.
        """

        self.group_box_audio_devices.setEnabled(status)
        self.group_box_buttons_for_sounds.setEnabled(status)
        self.line_edit_delay_time.setEnabled(status)
        self.button_start.setEnabled(status)

    def _init_audio_devices(self) -> QGroupBox:
        """
        Method initializes combo box widget with available audio devices.
        :return: group box widget with audio devices.
        """

        self.list_widget_audio_devices: QComboBox = QComboBox()
        self.list_widget_audio_devices.addItems(self.audio_devices)
        self.list_widget_audio_devices.currentIndexChanged.connect(self.set_audio_device)
        layout = QVBoxLayout()
        layout.addWidget(self.list_widget_audio_devices)
        self.group_box_audio_devices = QGroupBox("Available audio devices")
        self.group_box_audio_devices.setLayout(layout)
        return self.group_box_audio_devices

    def _init_buttons_for_sounds(self) -> QGroupBox:
        """
        Method initializes buttons. When buttons will be clicked corresponding
        sounds will be played.
        :return: group box widget with buttons.
        """

        grid_layout = QGridLayout()
        row = 0
        column = 0
        for file_name in sorted(os.listdir(self.dir_name)):
            button = QPushButton(file_name)
            button.clicked.connect(self.play_sound)
            grid_layout.addWidget(button, row, column)
            column += 1
            if column > 2:
                row += 1
                column = 0
        self.group_box_buttons_for_sounds = QGroupBox("Buttons for sounds")
        self.group_box_buttons_for_sounds.setLayout(grid_layout)
        return self.group_box_buttons_for_sounds

    def _init_periodic_widgets(self) -> QGroupBox:
        """
        Method initializes widgets to play sounds in loop.
        :return: group box widget with widgets.
        """

        form_layout = QFormLayout()
        self.line_edit_delay_time = QLineEdit()
        form_layout.addRow(QLabel("Time delay, ms"), self.line_edit_delay_time)
        v_layout = QVBoxLayout()
        v_layout.addLayout(form_layout)
        self.button_start: QPushButton = QPushButton("Start")
        self.button_start.clicked.connect(self.start)
        v_layout.addWidget(self.button_start)
        self.button_stop: QPushButton = QPushButton("Stop")
        self.button_stop.clicked.connect(self.stop)
        v_layout.addWidget(self.button_stop)
        self.group_box_periodic_widgets: QGroupBox = QGroupBox("Periodic work")
        self.group_box_periodic_widgets.setLayout(v_layout)
        return self.group_box_periodic_widgets

    def _init_ui(self):
        """
        Method initializes widgets on main window.
        """

        self.setWindowTitle("AudioPlayer")
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gui", "icon.png")
        self.setWindowIcon(QIcon(icon_path))
        self.setMaximumSize(500, 500)
        v_layout = QVBoxLayout()
        v_layout.addWidget(self._init_audio_devices())
        v_layout.addWidget(self._init_buttons_for_sounds())
        v_layout.addWidget(self._init_periodic_widgets())
        self.text_edit = QTextEdit()
        v_layout.addWidget(self.text_edit)
        widget = QWidget()
        widget.setLayout(v_layout)
        self.setCentralWidget(widget)
        if self.audio_devices:
            self.set_audio_device(0)

    @pyqtSlot()
    def play_sound(self):
        """
        Slot sends signal to play given sound.
        """

        sound = self.sender().text()
        self.certain_sound_required.emit(sound)

    @pyqtSlot(str)
    def print_info_about_sound(self, sound_name: str):
        """
        Slot prints information about sound being played.
        :param sound_name: name of sound being played.
        """

        message = f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S:%f')} {sound_name}"
        print(message)
        self.text_edit.append(message)

    @pyqtSlot(int)
    def set_audio_device(self, device_index: int):
        """
        Slot sets new audio device to play sounds.
        :param device_index: index of device in audio device list.
        """

        audio_device = self.audio_devices[device_index]
        pygame.mixer.init(devicename=audio_device)
        message = f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S:%f')} New audio device was set: {audio_device}"
        print(message)
        self.text_edit.append(message)

    @pyqtSlot()
    def start(self):
        """
        Slot starts loop to play sounds in list.
        """

        try:
            delay_time = int(self.line_edit_delay_time.text())
        except Exception:
            self.text_edit.append(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S:%f')} Wrong delay time value "
                                  f"{self.line_edit_delay_time.text()}")
            return
        self._enable_widgets(False)
        self.text_edit.append(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S:%f')} Launched periodic player "
                              f"with delay time {delay_time} msec")
        self.timer.setInterval(delay_time)
        self.timer.start()

    @pyqtSlot()
    def stop(self):
        """
        Slot stops loop to play sound in list.
        """

        self.timer.stop()
        self._enable_widgets()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    thread_for_player: ThreadForPlayer = ThreadForPlayer()
    window = MainWindow(thread_for_player.audio_devices)
    thread_for_player.sound_played.connect(window.print_info_about_sound, type=Qt.QueuedConnection)
    window.certain_sound_required.connect(thread_for_player.play_sound, type=Qt.QueuedConnection)
    window.sounds_required.connect(thread_for_player.play_next_sound, type=Qt.QueuedConnection)
    thread_for_player.start()
    window.show()
    sys.exit(app.exec_())
