# coding: utf-8
from wisun_manager_factory import WisunManagerFactory
from ethernet_manager import EthernetManager
from property_manager import PropertyManager
from logging import getLogger, StreamHandler, INFO, Formatter, DEBUG
import time
from btn_drv import ButtonDriver, POWER, SW2, SW3, SW4
from view_manager_power import ViewManagerPower
# from view_manager import ViewManagerAnalog
from view_manager_info import ViewManagerInfo
from enum import Enum
import os
from threading import Event, Thread
import signal
import sys
from configparser import ConfigParser

# ログの設定
handler = StreamHandler()
handler.setLevel(DEBUG)
handler.setFormatter(Formatter(
    "[%(asctime)s] [%(levelname)s] [%(threadName)s] [%(name)s] %(message)s"))
logger = getLogger()
logger.addHandler(handler)
logger.setLevel(INFO)

# config
iniFile = ConfigParser()
iniFile.read(os.path.abspath('./config.ini'))
fontInfo = int(iniFile.get('view', 'font_info'))
fontSmall = int(iniFile.get('view', 'font_small'))

# Wi-SUNマネージャ
wm = WisunManagerFactory.createInstance()
# Ethernetマネージャ
em = EthernetManager()
# Propertyマネージャ
pm = PropertyManager()
pm.setWisunManager(wm)
pm.setEthernetManager(em)
# Viewマネージャ
vmi = ViewManagerInfo(iniFile)
vmp = ViewManagerPower(iniFile)
vmp.setPropertyManager(pm)


class ConnectState(Enum):
    DISCONNECTED = 0
    CONNECTING = 1
    CONNECTED = 2
    CONNECT_ERROR = 3
    DEVICE_ERROR = 4
    DISCONNECTING = 5


thread = None
if wm is None:
    connect_state = ConnectState.DEVICE_ERROR
else:
    connect_state = ConnectState.DISCONNECTED


def main():
    global thread
    global connect_state

    signal.signal(signal.SIGTERM, termed)

    bd = ButtonDriver()

    # EthernetベースのEchonet処理開始
    em.start()

    vm = vmi
    pre_state = connect_state
    while True:
        if bd.isPressed(SW4):
            state = vm.get_display_state()
            vm.set_display_state(not state)
        if connect_state == ConnectState.CONNECTED:
            if bd.isPressed(SW3) and thread is None:
                stopConnect()
        elif connect_state == ConnectState.DISCONNECTED:
            vmi.setInfo('未接続', fontInfo)
            if bd.isPressed(SW2) and thread is None:
                startConnect()
        elif connect_state == ConnectState.DISCONNECTING:
            vmi.setInfo('切断中', fontInfo)
        elif connect_state == ConnectState.CONNECTING:
            vmi.setInfo('接続中', fontInfo)
        elif connect_state == ConnectState.CONNECT_ERROR:
            vmi.setInfo('接続失敗', fontInfo)
            if bd.isPressed(SW2) and thread is None:
                startConnect()
        elif connect_state == ConnectState.DEVICE_ERROR:
            vmi.setInfo('無線モジュール異常', fontSmall)
        if connect_state == ConnectState.CONNECTED:
            vm = vmp
        else:
            vm = vmi
        if pre_state != connect_state:
            vm.clearPayload()
        vm.reflesh()
        pre_state = connect_state

        if bd.isLongPressed(POWER):
            logger.info('pressed')
            vmi.setInfo('シャットダウン中', fontSmall)
            vm = vmi
            vm.clearPayload()
            vm.reflesh()
            # 終了処理
            bd.enablePowerButton()
            dispose()
            # シャットダウンコマンド
            os.system('sudo shutdown -h now')
            return
        time.sleep(0.1)

# Wi-SUN接続タスク起動
def startConnect():
    if wm is None:
        return
    global thread
    global connect_state
    connect_state = ConnectState.CONNECTING
    thread = Thread(target=connect_task)
    thread.start()

# Wi-SUN接続タスク
def connect_task():
    global thread
    global connect_state
    # スマートメータ接続
    logger.info('接続開始')
    connected = wm.connect()
    if connected:
        logger.info('接続成功')
        connect_state = ConnectState.CONNECTED
    else:
        logger.info('接続失敗')
        connect_state = ConnectState.CONNECT_ERROR
    thread = None

# Wi-SUN切断タスク起動
def stopConnect():
    if wm is None:
        return
    global thread
    global connect_state
    connect_state = ConnectState.DISCONNECTING
    thread = Thread(target=disconnect_task)
    thread.start()

# Wi-SUN切断タスク
def disconnect_task():
    global thread
    global connect_state
    # スマートメータ切断
    logger.info('切断開始')
    wm.disconnect()
    logger.info('切断成功')
    connect_state = ConnectState.DISCONNECTED
    thread = None

def dispose():
    # EthernetベースのEchonet処理終了
    em.stop()
    # スマートメータ切断
    if wm is not None:
        wm.disconnect()
        wm.dispose()


def termed(signum, frame):
    logger.info('SIGTERM!')
    dispose()
    sys.exit(0)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info('KeyboardInterrupt')
        dispose()
