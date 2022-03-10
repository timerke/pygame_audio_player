import datetime
import os
import platform
import sys
import time
from queue import Queue
from typing import List
import pygame
import pygame._sdl2 as sdl2
from epsound import WavFile, WavPlayer
from PyQt5.QtCore import pyqtSignal, pyqtSlot, QRegExp, Qt, QThread, QTimer
from PyQt5.QtGui import QIcon, QRegExpValidator
from PyQt5.QtWidgets import (QApplication, QComboBox, QFormLayout, QGridLayout, QGroupBox, QHBoxLayout, QLabel,
                             QLineEdit, QMainWindow, QPushButton, QTextEdit, QVBoxLayout, QWidget)

AUDIO_LIBRARIES = "epsound", "pygame"


class ThreadForPlayer(QThread):
    """
    Class for thread to play sounds.
    """

    sound_played = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._finish_time: float = None
        self._index: int = 0
        self._queue: Queue = Queue()
        self._sound_names: List[str] = []
        self._sounds: List[WavFile] = []
        self._wav_player: WavPlayer = WavPlayer(False)
        self._dir_name: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audio")
        for index, file_name in enumerate(sorted(os.listdir(self._dir_name))):
            self._sounds.append(WavFile(os.path.join(self._dir_name, file_name)))
            self._sound_names.append(file_name)
            self._wav_player.add_sound(os.path.join(self._dir_name, file_name), file_name)
        pygame.init()
        self.audio_devices: list = sdl2.get_audio_device_names()
        pygame.mixer.init()

    def _play_sound(self):
        """
        Method plays sound.
        """

        sound, sound_name, library, device = self._queue.get()
        if library == "pygame":
            path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audio", sound_name)
            pygame_sound = pygame.mixer.Sound(path)
            pygame_sound.play()
        else:
            if device:
                self._wav_player.set_device(device)
            else:
                self._wav_player.remove_device()
            self._wav_player.play(sound_name)
        self._finish_time = time.time() + sound.duration + 0.1
        self.sound_played.emit(sound_name)

    @pyqtSlot(str, str)
    def play_next_sound(self, library: str, device: str):
        """
        Slot plays next sound from list.
        :param library: audio library to play sound;
        :param device: audio device to play sound.
        """

        if self._index >= len(self._sound_names):
            self._index = 0
        self._queue.put((self._sounds[self._index], self._sound_names[self._index], library, device))
        self._index += 1

    @pyqtSlot(str, str, str)
    def play_sound_by_name(self, sound_name: str, library: str, device: str):
        """
        Slot plays sound with given name.
        :param sound_name: name of sound to play;
        :param library: audio library to play sound;
        :param device: audio device to play sound.
        """

        for index, name in enumerate(self._sound_names):
            if name == sound_name:
                self._queue.put((self._sounds[index], sound_name, library, device))
                break

    def run(self):
        while True:
            if not self._queue.empty() and (self._finish_time is None or time.time() > self._finish_time):
                self._play_sound()
            else:
                time.sleep(0.1)

    @pyqtSlot()
    def stop_current_queue(self):
        """
        Slot stops and clears current queue of sounds.
        """

        self._queue.queue.clear()


class MainWindow(QMainWindow):
    """
    Class with main window of application.
    """

    certain_sound_required = pyqtSignal(str, str, str)
    sounds_not_required = pyqtSignal()
    sounds_required = pyqtSignal(str, str)

    def __init__(self, audio_devices: list):
        """
        :param audio_devices: list of available audio devices.
        """

        super().__init__()
        self.audio_devices: list = audio_devices
        self.dir_name: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audio")
        self.timer: QTimer = QTimer()
        self.timer.timeout.connect(self.send_signal_to_play_next_sound)
        self.timer.setInterval(100)
        self.timer.setSingleShot(False)
        self._init_ui()

    def _enable_widgets(self, status: bool = True):
        """
        Method enables or disables some widgets.
        :param status: if True widgets will be enabled.
        """

        self.group_box_audio_libraries.setEnabled(status)
        self.group_box_buttons_for_sounds.setEnabled(status)
        self.line_edit_delay_time.setEnabled(status)
        self.button_start.setEnabled(status)

    def _get_device(self) -> str:
        """
        Method returns audio device to play sound.
        :return: audio device.
        """

        if self.list_widget_audio_devices.isVisible():
            return self.list_widget_audio_devices.currentText()
        if self.line_edit_audio_device.isVisible():
            return self.line_edit_audio_device.text()
        return ""

    def _init_audio_libraries(self) -> QGroupBox:
        """
        Method initializes group box widget with available audio libraries.
        :return: group box widget with audio libraries.
        """

        self.group_box_audio_libraries: QGroupBox = QGroupBox("Select audio library and device")
        self.list_widget_audio_libraries: QComboBox = QComboBox()
        self.list_widget_audio_libraries.addItems(AUDIO_LIBRARIES)
        self.list_widget_audio_libraries.currentIndexChanged.connect(self.show_audio_devices)
        h_layout_1 = QHBoxLayout()
        h_layout_1.addWidget(QLabel("Library"))
        h_layout_1.addWidget(self.list_widget_audio_libraries)

        self.label_audio_devices: QLabel = QLabel("Device")
        self.list_widget_audio_devices: QComboBox = QComboBox()
        self.list_widget_audio_devices.addItems(self.audio_devices)
        self.list_widget_audio_devices.currentIndexChanged.connect(self.set_audio_device)
        self.line_edit_audio_device: QLineEdit = QLineEdit()
        h_layout_2 = QHBoxLayout()
        h_layout_2.addWidget(self.label_audio_devices)
        h_layout_2.addWidget(self.list_widget_audio_devices)
        h_layout_2.addWidget(self.line_edit_audio_device)
        self.show_audio_devices(0)

        layout = QVBoxLayout()
        layout.addLayout(h_layout_1)
        layout.addLayout(h_layout_2)
        self.group_box_audio_libraries.setLayout(layout)
        return self.group_box_audio_libraries

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
            button.clicked.connect(self.play_sound_by_name)
            grid_layout.addWidget(button, row, column)
            column += 1
            if column > 2:
                row += 1
                column = 0
        self.group_box_buttons_for_sounds: QGroupBox = QGroupBox("Buttons for sounds")
        self.group_box_buttons_for_sounds.setLayout(grid_layout)
        return self.group_box_buttons_for_sounds

    def _init_periodic_widgets(self) -> QGroupBox:
        """
        Method initializes widgets to play sounds in loop.
        :return: group box widget with widgets.
        """

        form_layout = QFormLayout()
        self.line_edit_delay_time: QLineEdit = QLineEdit()
        self.line_edit_delay_time.setValidator(QRegExpValidator(QRegExp(r"\d+")))
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
        v_layout = QVBoxLayout()
        v_layout.addWidget(self._init_audio_libraries())
        v_layout.addWidget(self._init_buttons_for_sounds())
        v_layout.addWidget(self._init_periodic_widgets())
        v_layout.addStretch(1)

        self.text_edit: QTextEdit = QTextEdit()
        h_layout = QHBoxLayout()
        h_layout.addLayout(v_layout)
        h_layout.addWidget(self.text_edit, stretch=1)
        widget = QWidget()
        widget.setLayout(h_layout)
        self.setCentralWidget(widget)
        if self.audio_devices:
            self.set_audio_device(0)

    @pyqtSlot()
    def play_sound_by_name(self):
        """
        Slot sends signal to play given sound.
        """

        sound = self.sender().text()
        self.certain_sound_required.emit(sound, self.list_widget_audio_libraries.currentText(), self._get_device())

    @pyqtSlot(str)
    def print_info_about_sound(self, sound_name: str):
        """
        Slot prints information about sound being played.
        :param sound_name: name of sound being played.
        """

        message = f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S:%f')} {sound_name}"
        print(message)
        self.text_edit.append(message)

    @pyqtSlot()
    def send_signal_to_play_next_sound(self):
        """
        Slot sends signal to play next sound.
        """

        self.sounds_required.emit(self.list_widget_audio_libraries.currentText(), self._get_device())

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

    @pyqtSlot(int)
    def show_audio_devices(self, library_index: int):
        """
        Slot shows required audio devices for selected audio library.
        :param library_index: index of selected audio library.
        """

        if AUDIO_LIBRARIES[library_index] == "pygame":
            self.label_audio_devices.setVisible(True)
            self.line_edit_audio_device.setVisible(False)
            self.list_widget_audio_devices.setVisible(True)
        elif AUDIO_LIBRARIES[library_index] == "epsound" and platform.system().lower() == "linux":
            self.label_audio_devices.setVisible(True)
            self.line_edit_audio_device.setVisible(True)
            self.list_widget_audio_devices.setVisible(False)
        else:
            self.label_audio_devices.setVisible(False)
            self.line_edit_audio_device.setVisible(False)
            self.list_widget_audio_devices.setVisible(False)

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
        self.sounds_not_required.emit()
        self._enable_widgets()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    thread_for_player: ThreadForPlayer = ThreadForPlayer()
    window = MainWindow(thread_for_player.audio_devices)
    thread_for_player.sound_played.connect(window.print_info_about_sound, type=Qt.QueuedConnection)
    window.certain_sound_required.connect(thread_for_player.play_sound_by_name, type=Qt.QueuedConnection)
    window.sounds_not_required.connect(thread_for_player.stop_current_queue)
    window.sounds_required.connect(thread_for_player.play_next_sound, type=Qt.QueuedConnection)
    thread_for_player.start()
    window.show()
    sys.exit(app.exec_())
