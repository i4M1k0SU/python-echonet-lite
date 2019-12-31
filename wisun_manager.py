# coding: utf-8
from abc import ABCMeta, abstractmethod
from gpiozero import LED
import serial
from time import sleep
from threading import Event, Thread
from echonet_lite import Object, Frame, Node, Property
from queue import Queue, Empty
from set_queue import SetQueue
from logging import getLogger, StreamHandler, INFO, Formatter
logger = getLogger(__name__)


class ComError(Exception):
    pass

# Wi-SUNマネージャ基底クラス


class WisunManager(metaclass=ABCMeta):
    # 初期化
    def __init__(self, pwd, bid, dev):
        try:
            # Wi-SUN
            self._pwd = pwd
            self._bid = bid
            # シリアルポート初期化
            self._ser = serial.Serial(dev, 115200)
            self._ser.timeout = 5.0
            self._ser.write_timeout = 2.0
        except serial.SerialException:
            logger.error('Serial port Error')
            self._ser = None
        finally:
            # reset
            self._reset = LED(18, False)
            self.reset()
            # 受信タスク開始
            self.startReceiveTask()
            # 送信タスク用リソース
            self._sndThread = None
            self._queueSend = None
            self._propMan = None
            self._sendPause = False

    # シリアル送信
    def _serialSendLine(self, str):
        if self._ser is None:
            return False
        try:
            self._ser.write(str)
            return True
        except serial.serialutil.SerialTimeoutException:
            return False

    # シリアル受信（\rをデリミタとし、\nは読み飛ばす）
    def _serialReceiveLine(self):
        s = b''
        if self._ser is None:
            sleep(1)
            return s
        # return self._ser.readline()
        while True:
            c = self._ser.read(1)
            if c == b'\n':
                continue
            if c == b'' or c == b'\r':
                return s
            s += c

    # シリアル受信
    def _serialReceive(self, size):
        if self._ser is None:
            sleep(1)
            return b''
        return self._ser.read(size)

    # H/Wリセット
    def reset(self):
        logger.info('reset()')
        self._reset.on()
        sleep(0.5)
        self._reset.off()
        sleep(0.5)

    # 終了処理
    def dispose(self):
        logger.info('dispose')
        self.stopSendTask()
        self.stopReceiveTask()
        self._reset.close()
        if self._ser is not None:
            self._ser.close()

    # Propertyマネージャ設定
    def setPropertyManager(self, pm):
        self._propMan = pm

    # Propertyマネージャへ受信フレームを設定
    def putProperty(self, frame):
        if self._propMan is not None:
            keys = frame.get_key()
            self._propMan.put(frame, keys)

    # 受信キュー空読み
    def _clearReceiveQueue(self):
        if self._queueRecv is None:
            return
        # 受信キューが空になるまで空読み
        while True:
            try:
                r = self._queueRecv.get_nowait()
            except Empty:
                return

    # モジュール有効状態チェック
    @abstractmethod
    def isActive(self):
        pass

    # スマートメータにプロパティ要求
    def get(self, frame):
        if self._queueSend is not None:
            self._queueSend.put(frame)

    # 送信タスク開始
    def startSendTask(self):
        self._queueSend = SetQueue()
        self._sndThread = Thread(target=self._sndTask, args=(self._queueSend,))
        self._stopSendEvent = Event()
        self._sndThread.start()

    # 送信タスク終了
    def stopSendTask(self):
        if self._sndThread is None:
            return
        self._stopSendEvent.set()
        self._sndThread.join()
        self._sndThread = None

    # WiSUN送信タスク
    def _sndTask(self, queue):
        logger.info('send task start')
        req = Frame(bytearray([0x10, 0x81, 0x00, 0x01, 0x05, 0xff,
                               0x01, 0x02, 0x88, 0x01, 0x62, 0x02, 0xe7, 0x00, 0xe8, 0x00]))
        while not self._stopSendEvent.wait(15.0):
            if self._sendPause:
                continue
            try:
                frame = queue.get_nowait()
                self.wisunSendFrame(frame)
            except Empty:
                self.wisunSendFrame(req)
        logger.info('send task end')

    # 送信一時停止
    def sendPause(self, pause):
        self._sendPause = pause
        if pause:
            logger.info('Wi-SUN送信停止')
        else:
            logger.info('Wi-SUN送信再開')

    # Wi-SUN経由Echonet送信
    @abstractmethod
    def wisunSendFrame(self, frame: Frame):
        pass

    # 受信タスク開始
    @abstractmethod
    def startReceiveTask(self):
        pass

    # 受信タスク終了
    @abstractmethod
    def stopReceiveTask(self):
        pass

    # Wi-SUN切断
    @abstractmethod
    def disconnect(self):
        pass

    # Wi-SUN接続
    @abstractmethod
    def connect(self):
        pass
