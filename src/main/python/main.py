#!/usr/bin/env python3
from fbs_runtime.application_context.PyQt5 import ApplicationContext
import os
import sys
import stat
import json
import requests
from os.path import expanduser
from PyQt5 import uic
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from lib import guilib, rpclib, coinslib, wordlist, enc, priceslib, binance_api, botlib
from lib.qrcode import qr_popup
from lib.widgets import ScrollMessageBox
from lib.util import *
from lib.threads import *
import qrcode
import random
from ui import resources
import datetime
import time
from dateutil import parser
from zipfile import ZipFile 
import platform
import subprocess
import numpy as np
import pyqtgraph as pg
from pyqtgraph.Point import Point
import decimal
import logging
#from PyQt5.QtWebEngineWidgets import QWebEngineView

logger = logging.getLogger()
formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s', datefmt='%d-%b-%y %H:%M:%S')

# console logging
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
logger.addHandler(handler)

# File logging
fh = logging.FileHandler(sys.path[0]+'/debug.log')
fh.setLevel(logging.DEBUG)
fh.setFormatter(formatter)
logger.addHandler(fh)

home = expanduser("~")

# Attempt to suppress console window in windows version. TODO: not working, find another way.
if platform.system() == 'Windows':
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = subprocess.SW_HIDE
else:
    startupinfo = None

# scaling for high DPI vs SD monitors. Awaiting feedback from other users if any buttons etc are too small.
os.environ["QT_SCALE_FACTOR"] = "1"  
QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

# graph foreground / background colors
pg.setConfigOption('background', (64,64,64))
pg.setConfigOption('foreground', (78,155,46))

# Setup local settings config ini.
QSettings.setDefaultFormat(QSettings.IniFormat)
QCoreApplication.setOrganizationName("KomodoPlatform")
QCoreApplication.setApplicationName("AntaraMakerbot")
settings = QSettings()
ini_file = settings.fileName()
config_path = settings.fileName().replace("AntaraMakerbot.ini", "")

os.environ['MM_CONF_PATH'] = config_path+"MM2.json"

# Detect existing registered users
if settings.value('users') is None:
    settings.setValue("users", [])

# UI Class

class Ui(QTabWidget):
    def __init__(self, ctx):
        super(Ui, self).__init__() 
        # Load the User interface from file
        uifile = QFile(":/ui/makerbot_gui_dark_v4c_nograph.ui")
        uifile.open(QFile.ReadOnly)
        uic.loadUi(uifile, self) 
        self.ctx = ctx 
        self.show() 
        # define mm2 binary path
        try:
            self.mm2_bin = self.ctx.get_resource('mm2')
        except:
            self.mm2_bin = self.ctx.get_resource('mm2.exe')
        # define local bot api script
        try:
            self.bot_api = self.ctx.get_resource('mmbot_api')
        except:
            self.bot_api = self.ctx.get_resource('mmbot_api.exe')
        # define coins file path and set envornment variable for mm2 launch
        self.coins_file = self.ctx.get_resource('coins')
        os.environ['MM_COINS_PATH'] = self.coins_file
        # define qss (stylesheet) path and apply styling. 
        self.qss_file = self.ctx.get_resource('Darkeum.qss')
        with open(self.qss_file, 'r') as file:
            qss = file.read()
            self.setStyleSheet(qss)
                
        self.setWindowTitle("Komodo Platform's Antara Makerbot")
        self.setWindowIcon(QIcon(':/32/img/32/kmd.png'))


        #self.webframe_layout = QHBoxLayout()
        #self.webframe.setLayout(self.webframe_layout)
        self.authenticated = False
        self.mm2_downloading = False
        self.bot_trading = False
        self.countertrade_delay_limit = 1800

        self.last_price_update = 0
        self.prices_data = {
            "gecko":{},
            "paprika":{},
            "Binance":{},
            "average":{}
        }
        self.balances_data = {
            "mm2": {},
            "Binance": {}
        }

        # dict for the checkbox and label elements use on the coins activation page. Might be a better way to do this.
        self.gui_coins = {
            "BTC": {
                "checkbox": self.checkBox_btc, 
                "label": self.btc_label,    
            },
            "ETH": {
                "checkbox": self.checkBox_eth, 
                "label": self.eth_label,
            },
            "KMD": {
                "checkbox": self.checkBox_kmd, 
                "label": self.kmd_label,
            },
            "LABS": {
                "checkbox": self.checkBox_labs, 
                "label": self.labs_label,
            },
            "BCH": {
                "checkbox": self.checkBox_bch, 
                "label": self.bch_label,
            },
            "BAT": {
                "checkbox": self.checkBox_bat, 
                "label": self.bat_label,
            },
            "DOGE": {
                "checkbox": self.checkBox_doge, 
                "label": self.doge_label,
            },
            "DGB": {
                "checkbox": self.checkBox_dgb, 
                "label": self.dgb_label,
            },
            "DASH": {
                "checkbox": self.checkBox_dash, 
                "label": self.dash_label,
            },
            "LTC": {
                "checkbox": self.checkBox_ltc, 
                "label": self.ltc_label,
            },
            "ZEC": {
                "checkbox": self.checkBox_zec, 
                "label": self.zec_label,
            },
            "QTUM": {
                "checkbox": self.checkBox_qtum, 
                "label": self.qtum_label,
            },
            "AXE": {
                "checkbox": self.checkBox_axe, 
                "label": self.axe_label,
            },
            "VRSC": {
                "checkbox": self.checkBox_vrsc, 
                "label": self.vrsc_label,
            },
            "RFOX": {
                "checkbox": self.checkBox_rfox, 
                "label": self.rfox_label,
            },
            "ZILLA": {
                "checkbox": self.checkBox_zilla, 
                "label": self.zilla_label,
            },
            "HUSH": {
                "checkbox": self.checkBox_hush, 
                "label": self.hush_label,
            },
            "OOT": {
                "checkbox": self.checkBox_oot, 
                "label": self.oot_label,
            },
            "USDC": {
                "checkbox": self.checkBox_usdc, 
                "label": self.usdc_label,
            },
            "AWC": {
                "checkbox": self.checkBox_awc, 
                "label": self.awc_label,
            },
            "TUSD": {
                "checkbox": self.checkBox_tusd, 
                "label": self.tusd_label,
            },
            "PAX": {
                "checkbox": self.checkBox_pax, 
                "label": self.pax_label,
            },
            "RICK": {
                "checkbox": self.checkBox_rick, 
                "label": self.rick_label,
            },
            "MORTY": {
                "checkbox": self.checkBox_morty, 
                "label": self.morty_label,
            },
            "DAI": {
                "checkbox": self.checkBox_dai, 
                "label": self.dai_label,
            },
            "RVN": {
                "checkbox": self.checkBox_rvn, 
                "label": self.rvn_label,
            },
            "BOTS":{ 
                "checkbox":self.checkBox_bots, 
                "label":self.bots_label, 
            },
            "BTCH":{ 
                "checkbox":self.checkBox_btch, 
                "label":self.btch_label, 
            },
            "CHIPS":{ 
                "checkbox":self.checkBox_chips, 
                "label":self.chips_label, 
            },
            "COQUI":{ 
                "checkbox":self.checkBox_coqui, 
                "label":self.coqui_label, 
            },
            "CRYPTO":{ 
                "checkbox":self.checkBox_crypto, 
                "label":self.crypto_label, 
            },
            "DEX":{ 
                "checkbox":self.checkBox_dex, 
                "label":self.dex_label, 
            },
            "LINK":{ 
                "checkbox":self.checkBox_link, 
                "label":self.link_label, 
            },
            "REVS":{ 
                "checkbox":self.checkBox_revs, 
                "label":self.revs_label, 
            },
            "SUPERNET":{ 
                "checkbox":self.checkBox_supernet, 
                "label":self.supernet_label, 
            },
            "THC":{ 
                "checkbox":self.checkBox_thc, 
                "label":self.thc_label, 
            },
        }               
        self.show_login_tab()
                
    # once cachedata thred returns data, update balances, logs and tables as periodically.
    def update_cachedata(self, prices_dict, balances_dict):
        logger.info("Updating cache data from API")
        self.prices_data = prices_dict
        self.balances_data['mm2'].update(balances_dict['mm2'])
        self.balances_data["Binance"].update(balances_dict["Binance"])
        baserel = self.get_base_rel_from_combos(self.orderbook_sell_combo, self.orderbook_buy_combo, 'mm2')
        base = baserel[0]
        rel = baserel[1]
        self.update_mm2_balance_table()
        self.update_mm2_wallet_labels()
        self.update_binance_balance_table()
        self.update_prices_table()
        self.update_mm2_trade_history_table()
        self.update_strategy_history_table()
        self.update_strategies_table()
        self.view_strat_summary()
        self.update_mm2_orders_table()

        # TODO: Add gui update functions as req here.

    ## MM2 management
    # start MM2 for specific user
    def start_mm2(self, logfile='mm2_output.log'):
        try:
            global mm2_proc
            mm2_output = open(config_path+self.username+"_"+logfile,'w+')
            mm2_proc = subprocess.Popen([self.mm2_bin], stdout=mm2_output, stderr=mm2_output, universal_newlines=True, startupinfo=startupinfo)
            time.sleep(1)
        except Exception as e:
            QMessageBox.information(self, "MM2 status", 'No mm2 binary!')
            logger.info("MM2 Binary not found!")

    def start_api(self, logfile='bot_api_output.log'):
        try:
            global api_proc
            bot_api_output = open(config_path+self.username+"_"+logfile,'w+')
            api_proc = subprocess.Popen([self.bot_api, config_path], stdout=bot_api_output, stderr=bot_api_output, universal_newlines=True, startupinfo=startupinfo)
            time.sleep(1)
        except Exception as e:
            logger.info("MM2 Bot API did not start!")

    def launch_mm2(self):
        if self.username in settings.value('users'):
            self.username_input.setText('')
            self.password_input.setText('')
            # hide login page, show activation page
            self.stacked_login.setCurrentIndex(1)
            if self.creds[0] != '':
                if platform.system() == 'Windows':
                    kill_mm2 = subprocess.Popen(["tskill", "mm2.exe"], startupinfo=startupinfo)
                else:
                    kill_mm2 = subprocess.Popen(["pkill", "-9", "mm2"], startupinfo=startupinfo)
                kill_mm2.wait()
                i = 0
                version = ''
                while version == '':
                    try:
                        self.start_mm2()
                        time.sleep(1)
                        version = rpclib.version(self.creds[0], self.creds[1]).json()['result']
                        logger.info("mm2 version: "+version)
                        self.mm2_version_lbl.setText("MarketMaker version: "+version+" ")
                    except Exception as e:
                        logger.info('mm2 not start')
                        logger.info(e)
                        pass
                        i += 1
                        if i > 10:
                            QMessageBox.information(self, 'Error', "MM2 failed to start.\nCheck logs tab, or "+config_path+self.username+"_mm2_output.log", QMessageBox.Ok, QMessageBox.Ok)
                if platform.system() == 'Windows':
                    kill_api = subprocess.Popen(["tskill", "mmbot_api.exe"], startupinfo=startupinfo)
                else:
                    kill_api = subprocess.Popen(["pkill", "-9", "mmbot_api"], startupinfo=startupinfo)
                kill_api.wait()
                i = 0  
                version = ''
                while version == '':
                    try:
                        self.start_api()
                        time.sleep(1)
                        version = requests.get('http://127.0.0.1:8000/api_version').json()['version']
                        logger.info("Bot version: "+version)
                        self.api_version_lbl.setText("Makerbot API version: "+version+" ")
                    except Exception as e:
                        logger.info('bot not start')
                        logger.info(e)
                        pass
                        if i > 10:
                            QMessageBox.information(self, 'Error', "Bot API failed to start.\nCheck logs tab, or "+config_path+self.username+"_bot_output.log", QMessageBox.Ok, QMessageBox.Ok)
                if self.creds[5] == '':
                    key = 'x'
                else:
                    key = self.creds[5]
                if self.creds[6] == '':
                    secret = 'x'
                else:
                    secret = self.creds[6]
                endpoint = 'http://127.0.0.1:8000/set_creds?'
                params = 'ip='+self.creds[4]+'&rpc_pass='+self.creds[1]+'&key='+key+'&secret='+secret+'&username='+self.username
                url = endpoint+params
                requests.post(url)
                # purge MM2.json cleartext
                with open(config_path+"MM2.json", 'w+') as j:
                    j.write('')
                self.show_activation_tab()
                # stop zombie orders / strats
                self.stop_all_strats()
                rpclib.cancel_all(self.creds[0], self.creds[1]).json()
                binance_acct = binance_api.get_account_info(self.creds[5], self.creds[6])
                if 'code' in binance_acct:
                    self.authenticated_binance = False
                    self.binance_api_err = binance_acct['msg']
                else:
                    self.authenticated_binance = True
                    self.binance_api_err = ''
                # start data caching loop in other thread
                self.datacache_thread = cachedata_thread()
                self.datacache_thread.update_data.connect(self.update_cachedata)
                self.datacache_thread.start()
            else:
                self.setCurrentWidget(self.findChild(QWidget, 'tab_config'))

    def decrypt_creds(self):
        # create .enc if new user
        if not os.path.isfile(config_path+self.username+"_MM2.enc"):
            with open(config_path+self.username+"_MM2.enc", 'w') as f:
                f.write('')
        # create MM2.json if first run
        if not os.path.isfile(config_path+"MM2.json"):
            with open(config_path+"MM2.json", 'w') as f:
                f.write('')
        # decrypt user MM2.json
        else:
            with open(config_path+self.username+"_MM2.enc", 'r') as f:
                encrypted_mm2_json = f.read()
            if encrypted_mm2_json != '':
                mm2_json_decrypted = enc.decrypt_mm2_json(encrypted_mm2_json, self.password)
                try:
                    with open(config_path+"MM2.json", 'w') as j:
                        j.write(mm2_json_decrypted.decode())
                    self.authenticated = True
                except:
                    # did not decode, bad password
                    logger.info("decrypting failed")
                    pass
        jsonfile = config_path+"MM2.json"
        try:
            self.creds = guilib.get_creds(jsonfile)
        except Exception as e:
            logger.info("get_credentials failed")
            logger.info(e)
            self.creds = ['','','','','','','','','','']
            pass



    # spinbox operations
    def binance_bid_price_update(self):
        selected_row = self.binance_depth_table_bid.currentRow()
        if selected_row != -1 and self.binance_depth_table_bid.item(selected_row,1) is not None:
            price = self.binance_depth_table_bid.item(selected_row,1).text()
            self.binance_price_spinbox.setValue(float(price))
            #self.binance_depth_table_ask.clearSelection()

    def binance_ask_price_update(self):
        selected_row = self.binance_depth_table_ask.currentRow()
        if selected_row != -1 and self.binance_depth_table_ask.item(selected_row,1) is not None:
            price = self.binance_depth_table_ask.item(selected_row,1).text()
            self.binance_price_spinbox.setValue(float(price))
            #self.binance_depth_table_bid.clearSelection()

    # Selection menu operations
    def update_combo(self,combo,options,selected):
        combo.clear()
        options.sort()
        combo.addItems(options)
        if selected in options:
            for i in range(combo.count()):
                if combo.itemText(i) == selected:
                    combo.setCurrentIndex(i)
        else:
            combo.setCurrentIndex(0)
            selected = combo.itemText(combo.currentIndex())
        return selected

    def get_base_rel_from_combos(self, base_combo, rel_combo, api='mm2'):
        base = ''
        base_index = base_combo.currentIndex()
        if base_index != -1:
            base = base_combo.itemText(base_index)
        rel = ''
        rel_index = rel_combo.currentIndex()
        if rel_index != -1:
            rel = rel_combo.itemText(rel_index)
        if api == 'mm2':
            active_coins_selection = self.active_coins[:]
            if len(active_coins_selection) > 0:
                rel = self.update_combo(rel_combo,active_coins_selection,rel)
                active_coins_selection.remove(rel)
                base = self.update_combo(base_combo,active_coins_selection,base)
        elif api == "Binance":
            base_coins_selection = list(set(list(binance_api.base_asset_info.keys())) & set(self.active_coins[:]))
            if len(base_coins_selection) > 0:                
                base = self.update_combo(base_combo,base_coins_selection,base)
                rel_coins_selection = binance_api.base_asset_info[base]['quote_assets']
                rel = self.update_combo(rel_combo,rel_coins_selection,rel)
        return base, rel

    def update_active(self):
        self.active_coins = guilib.get_active_coins(self.creds[0], self.creds[1])
        for coin in self.gui_coins:
            if coin in self.active_coins:
                self.gui_coins[coin]['label'].setStyleSheet("background-color: rgb(78, 154, 6)")
                self.gui_coins[coin]['label'].setText("ACTIVE")
            else:
                self.gui_coins[coin]['label'].setStyleSheet("background-color: rgb(85, 87, 83)")
                self.gui_coins[coin]['label'].setText("INACTIVE")

    ## TABS ##
    def show_login_tab(self):
        self.stacked_login.setCurrentIndex(0)
        self.setCurrentWidget(self.findChild(QWidget, 'tab_activate'))
        self.username_input.setFocus()

    def show_activation_tab(self):
        self.update_active()
        self.update_activation_labels()
        self.update_activation_menu()

    def show_mm2_orderbook_tab(self):
        if len(self.active_coins) < 2:
            msg = 'Please activate at least two coins. '
            QMessageBox.information(self, 'Error', msg, QMessageBox.Ok, QMessageBox.Ok)
            self.setCurrentWidget(self.findChild(QWidget, 'tab_activate'))
        else:
            self.update_mm2_orderbook_table()
            self.update_mm2_orders_table()
            baserel = self.get_base_rel_from_combos(self.orderbook_sell_combo, self.orderbook_buy_combo, 'mm2')
            base = baserel[0]
            rel = baserel[1]
            self.update_mm2_orderbook_labels(base, rel)

    def show_binance_trading_tab(self):
        if len(self.active_coins) < 1:
            msg = 'Please activate at least one coin. '
            QMessageBox.information(self, 'Error', msg, QMessageBox.Ok, QMessageBox.Ok)
            self.setCurrentWidget(self.findChild(QWidget, 'tab_activate'))
        else:
            tickers = coinslib.binance_coins
            if tickers is not None:
                # wallet combobox
                self.update_combo(self.binance_asset_comboBox,tickers,tickers[0])
                # trade combobox
                baserel = self.get_base_rel_from_combos(self.binance_base_combo, self.binance_rel_combo, "Binance")
                base = baserel[0]
                rel = baserel[1]
                step_size = binance_api.base_asset_info[base]['stepSize']
                min_qty = binance_api.base_asset_info[base]['minQty']
                max_qty = binance_api.base_asset_info[base]['maxQty']
                self.binance_base_amount_spinbox.setSingleStep(float(step_size))
                self.binance_base_amount_spinbox.setRange(float(min_qty), float(max_qty))
                if not self.authenticated_binance:
                    msg = self.binance_api_err+"\n"
                    self.groupBox_bn_orders.setTitle("Binance API open Orders - "+msg)
                    self.groupBox_bn_orderbook.setTitle("Binance API Orderbook - "+msg)
                    self.groupBox_bn_balances.setTitle("Binance Balances - "+msg)
                else:
                    self.update_binance_orders_table()
                self.update_binance_labels(base, rel)
                self.update_binance_depth_table()

    def show_mm2_wallet_tab(self):
        if len(self.active_coins) < 1:
            msg = 'Please activate at least one coin. '
            QMessageBox.information(self, 'Error', msg, QMessageBox.Ok, QMessageBox.Ok)
            self.setCurrentWidget(self.findChild(QWidget, 'tab_activate'))
        else:
            self.wallet_recipient.setText('')
            self.wallet_amount.setValue(0)
            self.wallet_recipient.setFocus()
            if self.wallet_combo.currentIndex() != -1:
                selected = self.wallet_combo.itemText(self.wallet_combo.currentIndex())
            else:
                selected = self.wallet_combo.itemText(0)
            self.update_combo(self.wallet_combo,self.active_coins,selected)
            self.update_mm2_wallet_labels()
            self.update_mm2_balance_table()
            if selected == '':
                selected = self.wallet_combo.itemText(self.wallet_combo.currentIndex())
            '''
            tv_url = coinslib.coin_graph[selected]['url']
            tv_symbol = coinslib.coin_graph[selected]['symbol']
            tv_title = coinslib.coin_graph[selected]['title']

            if tv_url == '':
                tv_url = 'https://www.tradingview.com/symbols/NASDAQ-TSLA/'
                tv_symbol = 'NASDAQ:TSLA'
                tv_title = 'TESLA CHART'
            

            html = '<!DOCTYPE html>'
            html += '<html>'
            html += '<head>'
            html += '<title></title>'
            html += '</head>'
            html += '<body style="background:#333; margin:auto">'

            html += '<!-- TradingView Widget BEGIN --> \
                    <div class="tradingview-widget-container"> \
                      <div id="tradingview_41435"></div> \
                      <div class="tradingview-widget-copyright"><a href="'+tv_url+'" rel="noopener" target="_blank"><span class="blue-text">'+tv_symbol+'</span></a> by TradingView</div> \
                      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script> \
                      <script type="text/javascript"> \
                      new TradingView.widget( \
                      { \
                      "width": 1400, \
                      "height": 260, \
                      "symbol": "'+tv_symbol+'", \
                      "interval": "240", \
                      "timezone": "Etc/UTC", \
                      "theme": "Dark", \
                      "style": "3", \
                      "locale": "en", \
                      "toolbar_bg": "#f1f3f6", \
                      "enable_publishing": false, \
                      "allow_symbol_change": true, \
                      "container_id": "tradingview_41435" \
                    } \
                      ); \
                      </script> \
                    </div> \
                    <!-- TradingView Widget END -->' 

            html += '</body>'
            html += '</html>'

            web = Web()
            #web.load("https://www.tradingview.com/chart/?symbol=BINANCE%3AKMDBTC")
            web.load_html(html) 
            
            clearLayout(self.webframe_layout)
            self.webframe_layout.addWidget(web)
  '''

    def show_strategies_tab(self):
        self.update_strategies_table()
        self.populate_strategy_lists()

    def show_prices_tab(self):
        self.update_prices_table()
        # self.update_price_history_graph()

    def show_history_tab(self):
        logger.info('show_history_tab')
        self.update_mm2_trade_history_table()
        self.update_strategy_history_table()

    def show_config_tab(self):
        # populate credentials and config settings form fields
        if self.creds[0] != '':
            self.rpcpass_text_input.setText(self.creds[1])
            self.seed_text_input.setText(self.creds[2])
            self.netid_input.setValue(self.creds[3])
            self.rpc_ip_text_input.setText(self.creds[4])
            self.binance_key_text_input.setText(self.creds[5])
            self.binance_secret_text_input.setText(self.creds[6])
            if self.creds[4] == '127.0.0.1':
                self.checkbox_local_only.setChecked(True)
            else:
                self.checkbox_local_only.setChecked(False)

    def show_logs_tab(self):
        mm2_output = open(config_path+self.username+"_mm2_output.log",'r')
        with mm2_output as f:
            log_text = f.read()
            lines = f.readlines()
            self.scrollbar = self.mm2_console_logs.verticalScrollBar()
            self.mm2_console_logs.setStyleSheet("color: rgb(0, 0, 0); background-color: rgb(186, 189, 182);")
            self.mm2_console_logs.setPlainText(log_text)
            self.scrollbar.setValue(10000)
        api_output = open(config_path+self.username+"_bot_api_output.log",'r')
        with api_output as f:
            log_text = f.read()
            lines = f.readlines()
            self.scrollbar = self.api_console_logs.verticalScrollBar()
            self.api_console_logs.setStyleSheet("color: rgb(0, 0, 0); background-color: rgb(186, 189, 182);")
            self.api_console_logs.setPlainText(log_text)
            self.scrollbar.setValue(10000)

    ## LOGIN / ACTIVATE TAB FUNCTIONS
    def login(self):
        self.username = self.username_input.text()
        self.password = self.password_input.text()
        if self.username == '' or self.password == '' and not self.authenticated:
            QMessageBox.information(self, 'Login failed!', 'username and password fields can not be blank!', QMessageBox.Ok, QMessageBox.Ok)        
        else:
            self.decrypt_creds()
            if self.authenticated:   
                self.launch_mm2()
            elif self.username in settings.value('users'):
                QMessageBox.information(self, 'Login failed!', 'Incorrect username or password...', QMessageBox.Ok, QMessageBox.Ok)        
            else:
                resp = QMessageBox.information(self, 'User not found', 'Create new user?', QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if resp == QMessageBox.Yes:
                    settings.setValue('users', settings.value('users')+[self.username])
                    self.authenticated = True
                    self.setCurrentWidget(self.findChild(QWidget, 'tab_config'))
                elif resp == QMessageBox.No:
                    QMessageBox.information(self, 'Login failed!', 'Incorrect username or password...', QMessageBox.Ok, QMessageBox.Ok)        

    def logout(self):
        rpclib.stop_mm2(window.creds[0], window.creds[1])
        api_proc.kill()
        self.authenticated = False
        self.authenticated_binance = False
        self.username = ''
        self.password = ''
        self.creds = ['','','','','','','','','','']
        text_inputs = [self.seed_text_input, self.rpcpass_text_input, self.binance_key_text_input, self.binance_secret_text_input,
                       self.import_swaps_input, self.swap_recover_uuid]
        for text_input in text_inputs:
            text_input.setText('')
        tables = [self.orderbook_table, self.mm2_orders_table, self.binance_balances_table, self.binance_orders_table, 
                  self.wallet_balances_table, self.strategies_table, self.strat_summary_table, self.mm2_trades_table,
                  self.strategy_trades_table]
        for table in tables:
            table.clearContents()
        labels = [self.wallet_balance, self.wallet_locked_by_swaps, self.wallet_usd_value, self.wallet_btc_value, 
                  self.orderbook_buy_balance_lbl, self.orderbook_buy_locked_lbl, self.orderbook_sell_balance_lbl,
                  self.orderbook_sell_locked_lbl, self.binance_base_balance_lbl, self.binance_base_locked_lbl,
                  self.binance_quote_balance_lbl, self.binance_quote_locked_lbl, self.binance_addr_coin_lbl,
                  self.wallet_btc_total, self.wallet_usd_total] 
        for label in labels:
            label.setText('')
        time.sleep(0.2)
        self.prepare_tab()

    def activate_coins(self):
        coins_to_activate = []
        autoactivate = []
        for coin in self.gui_coins:
            label = self.gui_coins[coin]['label']
            checkbox = self.gui_coins[coin]['checkbox']
            # update buy/sell and autoactivate lists.
            if checkbox.isChecked():
                autoactivate.append(coin)
                if coin not in self.active_coins:
                    coins_to_activate.append([coin,label])
            activate_list = {
                "autoactivate":autoactivate,
            }
        with open(config_path+self.username+"_coins.json", 'w') as j:
            j.write(json.dumps(activate_list))
        # Activate selected coins in separate thread
        self.activate_thread = activation_thread(self.creds, coins_to_activate)
        self.activate_thread.activate.connect(self.update_active)
        self.activate_thread.start()
        # TODO: autoactivate coins needing kickstart
        logger.info("Kickstart coins: "+str(rpclib.coins_needed_for_kick_start(self.creds[0], self.creds[1]).json()))
        self.show_activation_tab()

    def update_activation_labels(self):
        for coin in self.gui_coins:
            self.gui_coins[coin]['checkbox'].hide()
            coin_label_txt = coinslib.coin_api_codes[coin]['name']
            coin_label_api = ""
            if coinslib.coin_api_codes[coin]['binance_id'] != '':
                coin_label_api += "ᵇ"
            if coinslib.coin_api_codes[coin]['coingecko_id'] != '':
                coin_label_api += "ᵍ"
            if coinslib.coin_api_codes[coin]['paprika_id'] != '':
                coin_label_api += "ᵖ"
            if coin_label_api != "":
                coin_label_api = " ⁽"+coin_label_api+"⁾"
            self.gui_coins[coin]['checkbox'].setText(coin_label_txt+coin_label_api)

    def update_activation_menu(self):
        display_coins_erc20 = []
        display_coins_utxo = []
        display_coins_smartchain = []
        search_txt = self.search_activate.text().lower()
        for coin in self.gui_coins:
            self.gui_coins[coin]['label'].hide()
            if coin.lower().find(search_txt) > -1 or self.gui_coins[coin]['checkbox'].text().lower().find(search_txt) > -1 or len(search_txt) == 0:
                if coinslib.coin_activation[coin]['type'] == 'utxo':
                    display_coins_utxo.append(coin)
                elif coinslib.coin_activation[coin]['type'] == 'erc20':
                    display_coins_erc20.append(coin)
                elif coinslib.coin_activation[coin]['type'] == 'smartchain':
                    display_coins_smartchain.append(coin)
            display_coins_erc20.sort()
            display_coins_utxo.sort()
            display_coins_smartchain.sort()
            self.populate_activation_menu(display_coins_smartchain, self.smartchains_layout)
            self.populate_activation_menu(display_coins_erc20, self.erc20_layout)
            self.populate_activation_menu(display_coins_utxo, self.utxo_layout)

    def populate_activation_menu(self, display_coins, layout):
        if os.path.exists(config_path+self.username+"_coins.json"):
            with open(config_path+self.username+"_coins.json", 'r') as j:
                user_coins = json.loads(j.read())
                user_autoactivate = user_coins['autoactivate']
        else:
            user_autoactivate = []

        row = 0
        for coin in display_coins:
            self.gui_coins[coin]['checkbox'].show()
            self.gui_coins[coin]['label'].show()
            layout.addWidget(self.gui_coins[coin]['checkbox'], row, 0, 1, 1)
            layout.addWidget(self.gui_coins[coin]['label'], row, 1, 1, 1)
            # set checkbox to ticked if in autoactivate list
            if coin in user_autoactivate:
                self.gui_coins[coin]['checkbox'].setChecked(True)
            else:
                self.gui_coins[coin]['checkbox'].setChecked(False)
            # set icon
            icon = QIcon()
            icon.addPixmap(QPixmap(":/32/img/32/"+coin.lower()+".png"), QIcon.Normal, QIcon.Off)
            self.gui_coins[coin]['checkbox'].setIcon(icon)
            row += 1

    def select_all(self, state, cointype):
        for coin in self.gui_coins:
            if coinslib.coin_activation[coin]['type'] == cointype:
                self.gui_coins[coin]['checkbox'].setChecked(state)

    def select_all_smart(self):
        state = self.checkBox_all_smartchains.isChecked()
        self.select_all(state, 'smartchain')

    def select_all_erc20(self):
        state = self.checkBox_all_erc20.isChecked()
        self.select_all(state, 'erc20')

    def select_all_utxo(self):
        state = self.checkBox_all_utxo.isChecked()
        self.select_all(state, 'utxo')

    def select_all_api(self):
        filter_list = []
        if self.checkBox_binance_compatible_checkbox.isChecked():
            filter_list.append("ᵇ")
        if self.checkBox_gecko_compatible_checkbox.isChecked():
            filter_list.append("ᵍ")
        if self.checkBox_paprika_compatible_checkbox.isChecked():
            filter_list.append("ᵖ")
        for coin in self.gui_coins:
            include_coin = ['True']
            for apitype in filter_list:
                if self.gui_coins[coin]['checkbox'].text().find(apitype) != -1:
                    include_coin.append('True')
                else:
                    include_coin.append('False')
            if 'False' not in include_coin:
                self.gui_coins[coin]['checkbox'].setChecked(True)
            else:
                self.gui_coins[coin]['checkbox'].setChecked(False)

    ## MARKETMAKER TAB FUNCTIONS
    def update_mm2_balance_from_thread(self, bal_info):
        if 'coin' in bal_info:
            coin = bal_info['coin']
            address = bal_info['address']
            total = bal_info['balance']
            locked = bal_info['locked_by_swaps']
            available = float(bal_info['balance']) - float(bal_info['locked_by_swaps'])
            self.balances_data["mm2"].update({coin: {
                    "address":address,
                    "total":total,
                    "locked":locked,
                    "available":available,
                    }                
                })

    def update_mm2_balance_table(self): 
        logger.info("Updating MM2 balance table")
        self.wallet_balances_table.clearContents()
        self.wallet_balances_table.setSortingEnabled(False)
        r = requests.get("http://127.0.0.1:8000/table/mm2_balances")
        if r.status_code == 200:
            if 'table_data' in r.json():
                table_data = r.json()['table_data']
                self.wallet_balances_table.setRowCount(len(table_data)-1)
                row = 0
                for row_data in table_data:
                    if row_data['Coin'] != 'TOTAL':
                        add_row(row, row_data.values(), self.wallet_balances_table)
                        row += 1
                self.adjust_cols(self.wallet_balances_table, table_data)
        self.wallet_kmd_total.setText("Total KMD Value: "+str(round(row_data['KMD Value'],4)))
        self.wallet_usd_total.setText("Total USD Value: $"+str(round(row_data['USD Value'],4)))
        self.wallet_btc_total.setText("Total BTC Value: "+str(round(row_data['BTC Value'],8)))
        self.wallet_balances_table.setSortingEnabled(True)
        self.wallet_balances_table.resizeColumnsToContents()
        self.wallet_balances_table.sortItems(0, Qt.AscendingOrder)

    def adjust_cols(self, table, data):
        max_col_str = {}
        if len(data) > 0:
            headers = list(data[0].keys())
            table.setColumnCount(len(headers))
            table.setHorizontalHeaderLabels(headers)
            for i in range(len(headers)):
                max_col_str[i] = str(headers[i])
            for item in data:
                row_data = list(item.values())
                for i in range(len(row_data)):
                    if len(str(row_data[i])) > len(str(max_col_str[i])):
                        max_col_str[i] = str(row_data[i])
        fontinfo = QFontInfo(table.font())
        print(max_col_str)
        for i in max_col_str:
            fm = QFontMetrics(QFont(fontinfo.family(), fontinfo.pointSize()))
            str_width = fm.width(max_col_str[i])
            table.setColumnWidth(i, str_width+10)


    def update_mm2_trades_table(self):
        swaps_info = rpclib.my_recent_swaps(self.creds[0], self.creds[1], limit=9999, from_uuid='').json()
        row = 0
        self.mm2_trades_table.setSortingEnabled(False)
        row_count = len(swaps_info['result']['swaps'])
        self.mm2_trades_table.setRowCount(row_count)
        for swap in swaps_info['result']['swaps']:
            for event in swap['events']:
                event_type = event['event']['type']
                if event_type in rpclib.error_events:
                    event_type = 'Failed'
                    break
            status = event_type
            role = swap['type']
            uuid = swap['uuid']
            my_amount = round(float(swap['my_info']['my_amount']),8)
            my_coin = swap['my_info']['my_coin']
            other_amount = round(float(swap['my_info']['other_amount']),8)
            other_coin = swap['my_info']['other_coin']
            started_at = datetime.datetime.fromtimestamp(round(swap['my_info']['started_at']/1000)*1000)
            if swap['type'] == 'Taker':
                buy_price = round(float(swap['my_info']['my_amount'])/float(swap['my_info']['other_amount']),8)
                sell_price = '-'
            else:
                buy_price = '-'
                sell_price = round(float(swap['my_info']['other_amount'])/float(swap['my_info']['my_amount']),8)
            trade_row = [started_at, role, status, other_coin, other_amount, buy_price, my_coin, my_amount, sell_price, uuid]
            add_row(row, trade_row, self.mm2_trades_table)
            row += 1
        self.mm2_trades_table.setSortingEnabled(True)
        #self.mm2_trades_table.resizeColumnsToContents()

    def update_mm2_orderbook_table(self):
        baserel = self.get_base_rel_from_combos(self.orderbook_sell_combo, self.orderbook_buy_combo, 'mm2')
        base = baserel[0]
        rel = baserel[1]
        # refresh tables
        if base != '' and rel != '':
            populate_table('', self.orderbook_table, self.orderbook_msg_lbl, "Click a row to buy "+rel+" from the Antara Marketmaker orderbook", "", "table/mm2_orderbook/"+rel+"/"+base)

    def update_mm2_orders_table(self):
        logger.info("Updating MM2 orders table")
        populate_table('', self.mm2_orders_table, self.mm2_orders_msg_lbl, "Highlight a row to select for cancelling order", "", "table/mm2_open_orders")

            
    def update_mm2_orderbook_labels(self, base, rel):
        self.orderbook_buy_amount_lbl.setText(""+rel+" Buy Amount")
        self.orderbook_sell_amount_lbl.setText(""+base+" Sell Amount")
        self.orderbook_price_lbl.setText(""+rel+" Buy Price in "+base)
        self.orderbook_sell_bal_icon.setText("<html><head/><body><p><img src=\":/64/img/64/"+base.lower()+".png\"/></p></body></html>")
        self.orderbook_buy_bal_icon.setText("<html><head/><body><p><img src=\":/64/img/64/"+rel.lower()+".png\"/></p></body></html>")
        self.orderbook_send_order_btn.setText("Buy "+rel)
        try:
            if base in self.balances_data['mm2']:
                locked_text = round(float(self.balances_data['mm2'][base]['locked']),8)
                balance = round(float(self.balances_data['mm2'][base]['total']),8)
            else:
                locked_text = round(float(0),8)
                balance = round(float(0),8)
        except:
                locked_text = '-'
                balance = '-'
        self.orderbook_sell_balance_lbl.setText("Available: "+str(balance)+" "+base)
        self.orderbook_sell_locked_lbl.setText("Locked: "+str(locked_text)+" "+base)
        try:
            if rel in self.balances_data['mm2']:
                locked_text = round(float(self.balances_data['mm2'][rel]['locked']),8)
                balance = round(float(self.balances_data['mm2'][rel]['total']),8)
            else:
                locked_text = round(float(0),8)
                balance = round(float(0),8)
        except:
                locked_text = '-'
                balance = '-'

        self.orderbook_buy_balance_lbl.setText("Available: "+str(balance)+" "+rel)
        self.orderbook_buy_locked_lbl.setText("Locked: "+str(locked_text)+" "+rel)
        
    # Order form button slots
    def mm2_orderbook_get_price(self):
        logger.info('get_price_from_orderbook')        
        selected_row = self.orderbook_table.currentRow()
        if selected_row != -1 and self.orderbook_table.item(selected_row,1) is not None:
            if self.orderbook_table.item(selected_row,3).text() != '':
                buy_coin = self.orderbook_table.item(selected_row,0).text()
                sell_coin = self.orderbook_table.item(selected_row,1).text()
                volume = self.orderbook_table.item(selected_row,2).text()
                price = self.orderbook_table.item(selected_row,3).text()
                value = self.orderbook_table.item(selected_row,4).text()
                sell_amount = self.orderbook_table.item(selected_row,5).text()
                try:
                    available_balance = float(self.balances_data['mm2'][sell_coin]['available'])
                except:
                    available_balance = 0
                logger.info("price: "+str(price))
                logger.info("available_balance: "+str(available_balance)+" "+sell_coin)
                logger.info("sell_amount: "+str(sell_amount)+" "+sell_coin)
                if float(sell_amount) > float(available_balance):
                    logger.info("using available balance")
                    sell_amount = float(available_balance)
                # set price and buy amount inputs from row selection
                self.orderbook_price_spinbox.setValue(float(price))
                self.orderbook_sell_amount_spinbox.setValue(float(sell_amount))


    def mm2_orderbook_combo_box_switch(self):
        logger.info('combo_box_switch')
        active_coins_selection = self.active_coins[:]
        index = self.orderbook_buy_combo.currentIndex()
        if index != -1:
            old_rel = self.orderbook_buy_combo.itemText(index)
        else:
            old_rel = ''
        index = self.orderbook_sell_combo.currentIndex()
        if index != -1:
            old_base = self.orderbook_sell_combo.itemText(index)
        else:
            old_base = ''
        if old_base == old_rel:
            old_base = ''
        rel = self.update_combo(self.orderbook_buy_combo,active_coins_selection,old_base)
        active_coins_selection.remove(rel)
        base = self.update_combo(self.orderbook_sell_combo,active_coins_selection,old_rel)
        self.orderbook_price_spinbox.setValue(0)
        self.orderbook_buy_amount_spinbox.setValue(0)
        self.orderbook_sell_amount_spinbox.setValue(0)
        self.show_mm2_orderbook_tab()

    def mm2_orderbook_combo_box_change(self):
        self.orderbook_price_spinbox.setValue(0)
        self.orderbook_buy_amount_spinbox.setValue(0)
        self.orderbook_sell_amount_spinbox.setValue(0)
        self.show_mm2_orderbook_tab()

    def mm2_orderbook_sell_pct(self, val):
        self.orderbook_sell_amount_spinbox.setValue(val)
        if self.orderbook_price_spinbox.value() != 0:
            price = self.orderbook_price_spinbox.value()
            self.orderbook_buy_amount_spinbox.setValue(val/price)

    def get_bal_pct(self, pct):
        bal = round(float(self.orderbook_sell_balance_lbl.text().split()[1]),8)
        return bal*pct/100

    def bal_25pct(self):
        val = self.get_bal_pct(25)
        self.mm2_orderbook_sell_pct(val)

    def bal_50pct(self):
        val = self.get_bal_pct(50)
        self.mm2_orderbook_sell_pct(val)

    def bal_75pct(self):
        val = self.get_bal_pct(75)
        self.mm2_orderbook_sell_pct(val)

    def bal_100pct(self):
        val = self.get_bal_pct(100)
        self.mm2_orderbook_sell_pct(val)

    # Dynamic order form price spinbox slots
    def update_mm2_orderbook_amounts(self, source=''):
        if source == '':
            sent_by = self.sender().objectName()
        else:
            sent_by = source
        logger.info("update mm2 values amounts (source: "+sent_by+")")
        orderbook_price_val = self.orderbook_price_spinbox.value()
        orderbook_sell_amount_val = self.orderbook_sell_amount_spinbox.value()
        orderbook_buy_amount_val = self.orderbook_buy_amount_spinbox.value()
        if sent_by == 'orderbook_price_spinbox':
            if orderbook_price_val != 0:
                if orderbook_buy_amount_val != 0:
                    orderbook_sell_amount_val = orderbook_buy_amount_val*orderbook_price_val
                    self.orderbook_sell_amount_spinbox.setValue(orderbook_sell_amount_val)
                elif orderbook_sell_amount_val != 0:
                    orderbook_buy_amount_val = orderbook_sell_amount_val/orderbook_price_val
                    self.orderbook_buy_amount_spinbox.setValue(orderbook_buy_amount_val)
        elif sent_by == 'orderbook_sell_amount_spinbox':
            if orderbook_sell_amount_val != 0:
                if orderbook_price_val != 0:
                    orderbook_buy_amount_val = orderbook_sell_amount_val/orderbook_price_val
                    self.orderbook_buy_amount_spinbox.setValue(orderbook_buy_amount_val)
        elif sent_by == 'orderbook_buy_amount_spinbox':
            if orderbook_buy_amount_val != 0:
                if orderbook_price_val != 0:                
                    orderbook_sell_amount_val = orderbook_buy_amount_val*orderbook_price_val
                    self.orderbook_sell_amount_spinbox.setValue(orderbook_sell_amount_val)

    def mm2_orderbook_buy_price_changed(self):
        self.update_mm2_orderbook_amounts('orderbook_price_spinbox')

    def mm2_orderbook_buy_amount_changed(self):
        self.update_mm2_orderbook_amounts('orderbook_buy_amount_spinbox')

    def mm2_orderbook_sell_amount_changed(self):
        self.update_mm2_orderbook_amounts('orderbook_sell_amount_spinbox')

    def mm2_orderbook_buy(self):
        index = self.orderbook_sell_combo.currentIndex()
        rel = self.orderbook_sell_combo.itemText(index)
        index = self.orderbook_buy_combo.currentIndex()
        base = self.orderbook_buy_combo.itemText(index)
        price = self.orderbook_price_spinbox.value()
        vol = self.orderbook_buy_amount_spinbox.value()
        #fee = get_fee(node_ip, user_pass, coin)
        trade_val = round(float(price)*float(vol),8)
        # get fee estimate
        try:
            trade_fee_resp = rpclib.get_fee(self.creds[0], self.creds[1], rel).json()
            logger.info("trade_fee_resp: "+str(trade_fee_resp))
            trade_fee = float(trade_fee_resp['result']['amount'])
        except Exception as e:
            logger.info("get_fee failed "+str(e))
            trade_fee = 0.001
        trade_vol = vol - float(trade_fee)*2
        resp = rpclib.buy(self.creds[0], self.creds[1], base, rel, trade_vol, price).json()
        if 'error' in resp:
            while resp['error'].find("too low, required") > -1:
                time.sleep(0.01)
                logger.info("trade_vol error: "+str(resp['error']))
                logger.info("reducing trade vol 1% and trying again...")
                trade_vol = trade_vol*0.99
                resp = rpclib.buy(self.creds[0], self.creds[1], base, rel, trade_vol, price).json()
                if 'error' not in resp:
                    break
        log_msg = "Buying "+str(vol)+" "+base +" for "+" "+str(trade_val)+" "+rel+" (fee estimate: "+str(trade_fee)+" "+rel+")"
        if 'error' in resp:
            if resp['error'].find("larger than available") > -1:
                msg = "Insufficient funds to complete order."
            else:
                msg = resp
        elif 'result' in resp:
            msg = "Order Submitted.\n"
            msg += "Buying "+str(vol)+" "+base +"\nfor\n"+" "+str(trade_val)+" "+rel+"\nFee estimate: "+str(trade_fee)+" "+rel
        else:
            msg = resp
        QMessageBox.information(self, 'Buy From Orderbook', str(msg), QMessageBox.Ok, QMessageBox.Ok)
        self.update_trading_log('mm2', log_msg, str(resp))

    def mm2_view_order(self):
        cancel = True
        selected_row = self.mm2_orders_table.currentRow()
        if self.mm2_orders_table.item(selected_row,8) is not None:
            mm2_order_uuid = self.mm2_orders_table.item(selected_row,8).text()
            order_info = rpclib.order_status(self.creds[0], self.creds[1], mm2_order_uuid).json()
            result = ScrollMessageBox(order_info)
            result.exec_()
            #QMessageBox.information(self, 'MM2 Order Info', json.dumps(order_info, indent=4), QMessageBox.Ok, QMessageBox.Ok)

    def mm2_cancel_order(self):
        cancel = True
        selected_row = self.mm2_orders_table.currentRow()
        if self.mm2_orders_table.item(selected_row,7) is not None:
            mm2_order_uuid = self.mm2_orders_table.item(selected_row,7).text()
            order_info = rpclib.order_status(self.creds[0], self.creds[1], mm2_order_uuid).json()
            logger.info("order_info: "+str(order_info))
            if len(order_info['order']['started_swaps']) != 0:
                swaps_in_progress = {}
                for swap_uuid in order_info['order']['started_swaps']:
                    swap_status = rpclib.my_swap_status(self.creds[0], self.creds[1], swap_uuid).json()
                    # TODO: Need an order with started swaps to test this further.
                    logger.info(swap_status)
                if len(swaps_in_progress) != 0:
                    msg = "This order has swaps in progress, are you sure you want to cancel it?"
                    msg += "\nSwaps in progress: \n"
                    for swap in swaps_in_progress:
                        msg += swap+": "+swaps_in_progress[swap]
                    confirm = QMessageBox.question(self, 'Cancel Order', msg, QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel, QMessageBox.Cancel)
                    if confirm == QMessageBox.No:
                        cancel = False
                    elif confirm == QMessageBox.Cancel:
                        cancel = False
            if cancel:
                resp = rpclib.cancel_uuid(self.creds[0], self.creds[1], mm2_order_uuid).json()
                msg = ''
                if 'result' in resp:
                    if resp['result'] == 'success':
                        msg = "Order "+mm2_order_uuid+" cancelled"
                    else:
                        msg = resp
                else:
                    msg = resp
                log_msg = "Cancelling mm2 order "+mm2_order_uuid+"..."
                self.update_trading_log("mm2", log_msg, str(resp))
                QMessageBox.information(self, 'Order Cancelled', str(msg), QMessageBox.Ok, QMessageBox.Ok)
        else:
            QMessageBox.information(self, 'Order Cancelled', 'No orders selected!', QMessageBox.Ok, QMessageBox.Ok)
        self.show_mm2_orderbook_tab()

    def mm2_cancel_all_orders(self):
        pending = 0
        cancel = True
        if self.mm2_trades_table.rowCount() != 0:
            for i in range(self.mm2_trades_table.rowCount()):
                if self.mm2_trades_table.item(i,2).text() != 'Finished' and self.mm2_trades_table.item(i,2).text() != 'Failed':
                    logger.info(self.mm2_trades_table.item(i,2).text())
                    pending += 1
            if pending > 0:
                msg = str(pending)+" order(s) have swaps in progress, are you sure you want to cancel all?"
                confirm = QMessageBox.question(self, 'Confirm Cancel Orders', msg, QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel, QMessageBox.Cancel)
                if confirm == QMessageBox.No:
                    cancel = False
                elif confirm == QMessageBox.Cancel:
                    cancel = False
            if cancel:
                resp = rpclib.cancel_all(self.creds[0], self.creds[1]).json()
                msg = ''
                if 'result' in resp:
                    if resp['result'] == 'success':
                        msg = "All your mm2 orders have been cancelled"
                    else:
                        msg = resp
                else:
                    msg = resp
                log_msg = "Cancelling all mm2 orders..."
                QMessageBox.information(self, 'MM2 Orders Cancelled', str(msg), QMessageBox.Ok, QMessageBox.Ok)
                self.update_trading_log("mm2", log_msg, str(resp))
        else:
            QMessageBox.information(self, 'Order Cancelled', 'You have no orders!', QMessageBox.Ok, QMessageBox.Ok)
        self.show_mm2_orderbook_tab()
   
    ## Binance Tab
    def bn_update_balance_from_thread(self, bal_info):
        logger.info('bn update_balance_from_thread')
        for coin in bal_info:
            total = bal_info[coin]['total']
            locked = bal_info[coin]['locked']
            available = bal_info[coin]['available']
            self.balances_data["Binance"].update({coin: {
                    "total":total,
                    "locked":locked,
                    "available":available,
                    "address":"Loading...",
                    }                
                })

    def binance_combo_box_change(self):
        self.binance_price_spinbox.setValue(0)
        self.binance_base_amount_spinbox.setValue(0)
        self.binance_quote_amount_spinbox.setValue(0)
        self.show_binance_trading_tab()

    def update_binance_labels(self, base, rel):
        self.binance_quote_icon.setText("<html><head/><body><p><img src=\":/64/img/64/"+rel.lower()+".png\"/></p></body></html>")
        self.binance_base_icon.setText("<html><head/><body><p><img src=\":/64/img/64/"+base.lower()+".png\"/></p></body></html>")
        if not self.authenticated_binance:
            self.binance_quote_balance_lbl.setText('Balance: Invalid API key!')
            self.binance_quote_locked_lbl.setText('Locked: Invalid API key!')
            self.binance_base_balance_lbl.setText('Balance: Invalid API key!')
            self.binance_base_locked_lbl.setText('Locked: Invalid API key!')    
        else:
            # Quote coin icon and balances
            if rel in self.balances_data["Binance"]:
                locked_text = "Locked: "+str(round(float(self.balances_data["Binance"][rel]['locked']),8))
                balance = "Balance: "+str(round(float(self.balances_data["Binance"][rel]['total']),8))
            else:
                locked_text = ""
                balance = "loading balance..."
            self.binance_quote_balance_lbl.setText(balance)
            self.binance_quote_locked_lbl.setText(locked_text)
            # Base coin icon and balances
            if base in self.balances_data["Binance"]:
                locked_text = "Locked: "+str(round(float(self.balances_data["Binance"][base]['locked']),8))
                balance = "Balance: "+str(round(float(self.balances_data["Binance"][base]['total']),8))
            else:
                locked_text = ""
                balance = "loading balance..."
            self.binance_base_balance_lbl.setText(balance)
            self.binance_base_locked_lbl.setText(locked_text)
        self.get_binance_addr()

    def update_binance_wallet(self):
        selected_row = self.binance_balances_table.currentRow()
        if selected_row != -1 and self.binance_balances_table.item(selected_row,0) is not None:
            coin = self.binance_balances_table.item(selected_row,0).text()
            self.update_combo(self.binance_asset_comboBox,coinslib.binance_coins,coin)
            self.get_binance_addr()

    def get_binance_addr(self):
        if not self.authenticated_binance:
            self.binance_qr_code_link.hide()
            self.binance_addr_lbl.setText("Invalid API key")
            self.binance_addr_coin_lbl.setText("")
        else:            
            index = self.binance_asset_comboBox.currentIndex()
            coin = self.binance_asset_comboBox.itemText(index)
            # start in other thread
            self.thread_addr_request = addr_request_thread(self.creds[5], self.creds[6], coin)
            self.thread_addr_request.resp.connect(self.update_binance_addr)
            self.thread_addr_request.start()

    def update_binance_addr(self, resp, coin):
        if 'address' in resp:
            addr_text = resp['address']
            self.binance_qr_code_link.show()
        else:
            addr_text = 'Address not found - create it at Binance.com'
            self.binance_qr_code_link.hide()
        self.binance_addr_lbl.setText(addr_text)
        self.binance_addr_coin_lbl.setText("Binance "+str(coin)+" Address")

    def update_binance_orders_table(self):
        logger.info('update_binance_orders_table')
        # populate binance depth table
        request_table_data("table/binance_open_orders", self.binance_orders_table, self.binance_orders_msg_lbl, "")

    def show_qr_popup(self):
        coin = self.binance_addr_coin_lbl.text().split()[1]
        addr_txt = self.binance_addr_lbl.text()
        mm2_qr = qr_popup("Binance "+coin+" Address QR Code", addr_txt)
        mm2_qr.show()


    def update_binance_balance_table(self):
        self.binance_balances_table.clearContents()
        if self.authenticated_binance:
            logger.info("Updating Binance balance table")
            row_count = len(self.balances_data["Binance"])
            self.binance_balances_table.setRowCount(row_count)
            self.binance_balances_table.setSortingEnabled(False)
            row = 0
            if row_count == 0:
                self.binance_balances_msg_lbl.setText('Balances loading...')
            else:
                self.binance_balances_msg_lbl.setText('')
                for coin in self.balances_data["Binance"]:
                    available = float(self.balances_data["Binance"][coin]['available'])
                    total = float(self.balances_data["Binance"][coin]['total'])
                    locked = float(self.balances_data["Binance"][coin]['locked'])
                    balance_row = [coin, format_num_10f(total), format_num_10f(available), format_num_10f(locked)]
                    add_row(row, balance_row, self.binance_balances_table)
                    row += 1
            self.binance_balances_table.setSortingEnabled(True)
            #self.binance_balances_table.sortItems(1, Qt.DescendingOrder)
            #self.binance_balances_table.resizeColumnsToContents()

    def update_binance_depth_table(self):
        index = self.binance_base_combo.currentIndex()
        base = self.binance_base_combo.itemText(index)
        index = self.binance_rel_combo.currentIndex()
        rel = self.binance_rel_combo.itemText(index)
        self.binance_price_spinbox.setValue(0)
        self.binance_price_lbl.setText("Price ("+rel+" per "+base+")")
        self.binance_base_amount_lbl.setText("Amount ("+base+")")
        self.binance_quote_amount_lbl.setText("Amount ("+rel+")")
        ticker_pair = base+rel
        # populate binance depth table
        request_table_data("table/get_binance_depth/"+ticker_pair,
                            self.binance_depth_table_bid,
                            "",
                            "",
                            "3|Bid|INCLUDE")
        request_table_data("table/get_binance_depth/"+ticker_pair,
                            self.binance_depth_table_ask,
                            "",
                            "",
                            "3|Ask|INCLUDE")
        # update button text
        self.binance_sell_btn.setText("Sell "+base)
        self.binance_buy_btn.setText("Buy "+base)

    def update_binance_price_val(self):
        # sets trade price to selected/clicked row on depth tables
        selected_row = self.binance_depth_table.currentRow()
        price = self.binance_depth_table.item(selected_row,1).text()
        order_type = self.binance_depth_table.item(selected_row,3).text()
        self.binance_price_spinbox.setValue(float(price))

    # Dynamic order form price spinbox slots
    def update_binance_orderbook_amounts(self, source=''):
        if source == '':
            sent_by = self.sender().objectName()
        else:
            sent_by = source
        logger.info("update binance values amounts (source: "+sent_by+")")
        index = self.binance_base_combo.currentIndex()
        baseAsset = self.binance_base_combo.itemText(index)
        index = self.binance_rel_combo.currentIndex()
        quoteAsset = self.binance_rel_combo.itemText(index)
        symbol = baseAsset+quoteAsset
        price_val = self.binance_price_spinbox.value()
        quote_amount_val = self.binance_quote_amount_spinbox.value()
        base_amount_val = self.binance_base_amount_spinbox.value()
        if sent_by == 'binance_price_spinbox':
            if price_val != 0:
                if base_amount_val != 0:
                    quote_amount_val = base_amount_val*price_val
                    self.binance_quote_amount_spinbox.setValue(quote_amount_val)
                elif quote_amount_val != 0:
                    base_amount_val = binance_api.round_to_step(symbol, quote_amount_val/price_val)
                    self.binance_base_amount_spinbox.setValue(base_amount_val)
        elif sent_by == 'binance_quote_amount_spinbox':
            if quote_amount_val != 0:
                if price_val != 0:
                    base_amount_val = binance_api.round_to_step(symbol, quote_amount_val/price_val)
                    self.binance_base_amount_spinbox.setValue(base_amount_val)
        elif sent_by == 'binance_base_amount_spinbox':
            if base_amount_val != 0:
                if price_val != 0:                
                    quote_amount_val = base_amount_val*price_val
                    self.binance_quote_amount_spinbox.setValue(quote_amount_val)

    def binance_price_changed(self):
        self.update_binance_orderbook_amounts('binance_price_spinbox')

    def binance_quote_amount_changed(self):
        self.update_binance_orderbook_amounts('binance_quote_amount_spinbox')

    def binance_base_amount_changed(self):
        self.update_binance_orderbook_amounts('binance_base_amount_spinbox')

    def binance_buy(self):
        qty = '{:.8f}'.format(self.binance_base_amount_spinbox.value())
        quote_qty = '{:.8f}'.format(self.binance_quote_amount_spinbox.value())
        price = '{:.8f}'.format(self.binance_price_spinbox.value())
        index = self.binance_base_combo.currentIndex()
        baseAsset = self.binance_base_combo.itemText(index)
        index = self.binance_rel_combo.currentIndex()
        quoteAsset = self.binance_rel_combo.itemText(index)
        symbol = baseAsset+quoteAsset
        logger.info(binance_api.binance_pair_info[symbol])
        min_notional = float(binance_api.binance_pair_info[symbol]['minNotional'])
        if float(quote_qty) < min_notional:
            QMessageBox.information(self, 'Buy Order Failed', "Trade value must be over "+str(min_notional)+" "+quoteAsset, QMessageBox.Ok, QMessageBox.Ok)
        else:
            resp = binance_api.create_buy_order(self.creds[5], self.creds[6], symbol, qty, price)
            log_msg = "Buy order submitted! "+str(qty)+" "+baseAsset+" at "+str(price)+" "+quoteAsset+" (Total: "+str(float(qty)*float(price))+" "+quoteAsset+")"
            if 'orderId' in resp:
                msg = "Buy order submitted!\n "+str(qty)+" "+baseAsset+" at "+str(price)+" "+quoteAsset+"\nTotal: "+str(float(qty)*float(price))+" "+quoteAsset
                QMessageBox.information(self, 'Buy Order Sent', msg, QMessageBox.Ok, QMessageBox.Ok)
            else:
                QMessageBox.information(self, 'Buy Order Failed', str(resp), QMessageBox.Ok, QMessageBox.Ok)
            self.update_trading_log('Binance', log_msg, str(resp))
        self.update_binance_orders_table()

    def binance_sell(self):
        qty = '{:.8f}'.format(self.binance_base_amount_spinbox.value())
        quote_qty = '{:.8f}'.format(self.binance_quote_amount_spinbox.value())
        price = '{:.8f}'.format(self.binance_price_spinbox.value())
        index = self.binance_base_combo.currentIndex()
        baseAsset = self.binance_base_combo.itemText(index)
        index = self.binance_rel_combo.currentIndex()
        quoteAsset = self.binance_rel_combo.itemText(index)
        symbol = baseAsset+quoteAsset
        min_notional = binance_api.binance_pair_info[symbol]['minNotional']
        if float(quote_qty) < float(min_notional):
            QMessageBox.information(self, 'Buy Order Failed', "Trade value must be over "+str(min_notional)+" "+quoteAsset, QMessageBox.Ok, QMessageBox.Ok)
        else:
            resp = binance_api.create_sell_order(self.creds[5], self.creds[6], symbol, qty, price)
            log_msg = "Sell order submitted! "+str(qty)+" "+baseAsset+" at "+str(price)+" "+quoteAsset+" (Total: "+str(float(qty)*float(price))+" "+quoteAsset+")"
            if 'orderId' in resp:
                msg = "Sell order submitted!\n "+str(qty)+" "+baseAsset+" at "+str(price)+" "+quoteAsset+"\nTotal: "+str(float(qty)*float(price))+" "+quoteAsset
                QMessageBox.information(self, 'Sell Order Sent', msg, QMessageBox.Ok, QMessageBox.Ok)
            else:
                QMessageBox.information(self, 'Sell Order Failed', str(resp), QMessageBox.Ok, QMessageBox.Ok)
            self.update_trading_log('Binance', log_msg, str(resp))
        self.update_binance_orders_table()

    def binance_withdraw(self):
        index = self.binance_asset_comboBox.currentIndex()
        coin = self.binance_asset_comboBox.itemText(index)
        addr = self.binance_withdraw_addr_lineEdit.text()
        amount = self.binance_withdraw_amount_spinbox.value()
        msg = ''
        confirm_msg = 'Confirm withdraw:\n\n'
        confirm_msg += str(amount)+' '+coin+' to '+addr+'\n\n'
        confirm_msg += "Check https://www.binance.com/en/fee/schedule for withdrawl fee details\n\n"
        confirm = QMessageBox.question(self, "Confirm withdraw?", confirm_msg, QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel, QMessageBox.Cancel)
        if confirm == QMessageBox.Yes:
            proceed = True
        else:
            proceed = False
        if proceed:
            resp = binance_api.withdraw(self.creds[5], self.creds[6], coin, addr, amount)
            if 'id' in resp:
                txid = resp['id']
                msg += "Sent!\n"
            else:
                msg += str(resp)
            QMessageBox.information(self, 'Binance Withdraw', str(msg), QMessageBox.Ok, QMessageBox.Ok)

    def binance_cancel_selected_order(self):
        selected_row = self.binance_orders_table.currentRow()
        if self.binance_orders_table.item(selected_row,0) is not None:
            order_id = self.binance_orders_table.item(selected_row,0).text()
            ticker_pair = self.binance_orders_table.item(selected_row,2).text()
            resp = binance_api.delete_order(self.creds[5], self.creds[6], ticker_pair, order_id)
            msg = ''
            if "status" in resp:
                if resp["status"] == "CANCELED":
                    msg = "Order "+order_id+" cancelled"
                else:
                    msg = resp
            else:
                msg = resp
            log_msg = "Cancelling Binance order "+str(order_id)+" ("+ticker_pair+")"
            self.update_trading_log("Binance", log_msg, str(resp))
            QMessageBox.information(self, 'Order Cancelled', str(msg), QMessageBox.Ok, QMessageBox.Ok)      
        else:
            QMessageBox.information(self, 'Order Cancelled', 'No orders selected!', QMessageBox.Ok, QMessageBox.Ok)        
        self.update_binance_orders_table()

    def binance_cancel_all_orders(self):
        open_orders = binance_api.get_open_orders(self.creds[5], self.creds[6])
        order_ids = []
        for item in open_orders:
            order_ids.append([item['orderId'],item['symbol']])
        for order_id in order_ids:
            resp = binance_api.delete_order(self.creds[5], self.creds[6], order_id[1], order_id[0])
            log_msg = "Cancelling Binance order "+str(order_id[0])+" ("+order_id[1]+")"
            self.update_trading_log("Binance", log_msg, str(resp))
            time.sleep(0.05)
            self.update_binance_orders_table()
        QMessageBox.information(self, 'Order Cancelled', 'All orders cancelled!', QMessageBox.Ok, QMessageBox.Ok)

    ## Prices Tab
    ## WALLET TAB
    def update_mm2_wallet_from_thread(self, bal_info):
        coin = bal_info['coin']
        address = bal_info['address']
        total = bal_info['balance']
        locked = bal_info['locked_by_swaps']
        available = float(bal_info['balance']) - float(bal_info['locked_by_swaps'])
        self.balances_data["mm2"].update({coin: {
                "address":address,
                "total":total,
                "locked":locked,
                "available":available,
                }                
            })
        if coin != '' and address != '':
            self.update_mm2_wallet_labels()

    def update_mm2_wallet_labels(self):      
        self.wallet_balance.setText('')
        self.wallet_address.setText('Loading...')
        self.wallet_locked_by_swaps.setText('')
        self.wallet_btc_value.setText("")
        self.wallet_usd_value.setText("")
        index = self.wallet_combo.currentIndex()     
        if index != -1:
            coin = self.wallet_combo.itemText(index)
            self.wallet_coin_img.setText("<html><head/><body><p><img src=\":/300/img/300/"+coin.lower()+".png\"/></p></body></html>")
            if coin in self.balances_data["mm2"]:
                address = self.balances_data["mm2"][coin]["address"]
                total = self.balances_data["mm2"][coin]["total"]
                locked = self.balances_data["mm2"][coin]["locked"]
                available = self.balances_data["mm2"][coin]["available"]
                if coinslib.coin_explorers[coin]['addr_explorer'] != '':
                    self.wallet_address.setText("<a href='"+coinslib.coin_explorers[coin]['addr_explorer']+"/"+address+"'><span style='text-decoration: underline; color:#eeeeec;'>"+address+"</span></href>")
                else:
                    self.wallet_address.setText(address)            
                self.wallet_balance.setText(total)
                self.wallet_locked_by_swaps.setText("locked by swaps: "+str(locked))
                # TODO: add value in KMD
                if coin in self.prices_data['average']:
                    usd_price = self.prices_data['average'][coin]['USD']
                    btc_price = self.prices_data['average'][coin]['BTC']
                    try:
                        usd_val = round(float(usd_price)*float(total),4)
                        btc_val = round(float(btc_price)*float(total),8)
                        self.wallet_usd_value.setText("$"+str(usd_val)+" USD")
                        self.wallet_btc_value.setText(str(btc_val)+" BTC")
                    except Exception as e:
                        usd_val = '-'
                        btc_val = '-'
                        self.wallet_usd_value.setText("$"+str(0)+" USD")
                        self.wallet_btc_value.setText(str(0)+" BTC")
                        logger.info('update wallet labels err (likely no price, setting to zero value)')

    def show_mm2_qr_popup(self):
        index = self.wallet_combo.currentIndex()
        coin = self.wallet_combo.itemText(index)
        addr_txt = self.balances_data["mm2"][coin]["address"]
        mm2_qr = qr_popup("MM2 "+coin+" Address QR Code ", addr_txt)
        mm2_qr.show()

    def select_wallet_from_table(self):
        selected_row = self.wallet_balances_table.currentRow()
        if selected_row != -1 and self.wallet_balances_table.item(selected_row,0) is not None:
            coin = self.wallet_balances_table.item(selected_row,0).text()
            self.wallet_balances_table.setRangeSelected(QTableWidgetSelectionRange(selected_row, 0, selected_row, 3), False)
            self.update_combo(self.wallet_combo,self.active_coins,coin)
            self.show_mm2_wallet_tab()

    def set_max_withdraw(self):
        index = self.wallet_combo.currentIndex()
        coin = self.wallet_combo.itemText(index)
        balance = self.balances_data["mm2"][coin]["available"]
        logger.info("send max "+balance)
        self.wallet_amount.setValue(float(balance))

    def set_self_withdraw(self):
        index = self.wallet_combo.currentIndex()
        coin = self.wallet_combo.itemText(index)
        addr_txt = self.balances_data["mm2"][coin]["address"]
        logger.info("self send to "+addr_txt)
        self.wallet_recipient.setText(addr_txt)

    # process withdrawl from wallet tab
    def send_funds(self):
        index = self.wallet_combo.currentIndex()
        coin = self.wallet_combo.itemText(index)
        recipient_addr = self.wallet_recipient.text()
        amount = self.wallet_amount.text()
        confirm = QMessageBox.question(self, 'Confirm send?', "Confirm sending "+str(amount)+" "+coin+" to "+recipient_addr+"?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if confirm == QMessageBox.Yes:
            msg = ''
            if float(amount) == float(self.balances_data["mm2"][coin]["available"]):
                logger.info("withdrawing max "+coin)
                resp = rpclib.withdraw_max(self.creds[0], self.creds[1], coin, recipient_addr).json()
            else:
                logger.info("withdrawing "+amount+" "+coin)
                resp = rpclib.withdraw(self.creds[0], self.creds[1], coin, recipient_addr, amount).json()
            if 'error' in resp:
                logger.info(resp['error'])
                if resp['error'].find("Invalid Address!") > -1:
                    msg += "Invalid Address"
                elif resp['error'].find("Not sufficient balance!") > -1:
                    msg += "Insufficient balance"
                elif resp['error'].find("less than dust amount") > -1:
                    msg += "Transaction value too small!"
                else:
                    msg = str(resp['error'])
            elif 'tx_hex' in resp:
                raw_hex = resp['tx_hex']
                resp = rpclib.send_raw_transaction(self.creds[0], self.creds[1], coin, raw_hex).json()
                # hyperlink tx in explorer if url in coinslib
                if 'tx_hash' in resp:
                    txid = resp['tx_hash']
                    if recipient_addr.startswith('0x'):
                        txid_str = '0x'+txid
                    else:
                        txid_str = txid
                    if coinslib.coin_explorers[coin]['tx_explorer'] != '':
                        txid_link = coinslib.coin_explorers[coin]['tx_explorer']+"/"+txid_str
                        msg = "Sent! <br /><a style='color:white !important' href='"+txid_link+"'>"+txid_link+"</a>"
                    else:
                        msg = "Sent! <br />TXID: ["+txid_str+"]"
                self.wallet_recipient.setText("")
                self.wallet_amount.setValue(0)
            else:
                msg = str(resp)
            QMessageBox.information(self, 'Wallet transaction', msg, QMessageBox.Ok, QMessageBox.Ok)
            self.update_mm2_wallet_labels()

    ## STRATEGIES TAB
    def populate_strategy_lists(self):
        logger.info('Populating strategy lists')
        self.strat_buy_list.clear()
        self.strat_sell_list.clear()
        self.strat_cex_list.clear()
        for coin in self.active_coins:
            if len(self.prices_data['average'][coin]['btc_sources']) > 0:
                if 'mm2_orderbook' not in self.prices_data['average'][coin]['btc_sources']:
                    buy_list_item = QListWidgetItem(coin)
                    buy_list_item.setTextAlignment(Qt.AlignHCenter)
                    self.strat_buy_list.addItem(buy_list_item)
                    sell_list_item = QListWidgetItem(coin)
                    sell_list_item.setTextAlignment(Qt.AlignHCenter)
                    self.strat_sell_list.addItem(sell_list_item)
        cex_list = requests.get('http://127.0.0.1:8000/cex/list').json()['cex_list']
        list_item = QListWidgetItem("None")
        list_item.setTextAlignment(Qt.AlignHCenter)
        self.strat_cex_list.addItem(list_item)
        for item in cex_list:
            list_item = QListWidgetItem(item)
            list_item.setTextAlignment(Qt.AlignHCenter)
            if item == 'Binance':
                if self.authenticated_binance:
                    self.strat_cex_list.addItem(list_item)
            else:
                self.strat_cex_list.addItem(list_item)

    def update_strategies_table(self):
        logger.info('Updating strategies table')
        populate_table('', self.strategies_table, self.strategies_msg_lbl, "Highlight a row to view strategy trade summary","","table/bot_strategies")
        row_fg(self.strategies_table, QColor(255, 233, 127), 10, ['inactive'], 'exclude')
        row_fg(self.strategies_table, QColor(218, 255, 127), 10, ['active'], 'include')
        self.strategies_table.clearSelection()

    def create_strat(self):
        params = 'name='+self.strat_name.text()
        index = self.strat_type_combo.currentIndex()
        strat_type = self.strat_type_combo.itemText(index)
        params += '&strategy_type='+strat_type
        buy_list = []
        for item in self.strat_buy_list.selectedItems():
            buy_list.append(item.text())
        sell_list = []
        for item in self.strat_sell_list.selectedItems():
            sell_list.append(item.text())
        cex_list = []
        for item in self.strat_cex_list.selectedItems():
            cex_list.append(item.text())
        buy_items = ','.join(buy_list)
        sell_items = ','.join(sell_list)
        cex_items = ','.join(cex_list)
        params += '&sell_list='+sell_items
        params += '&buy_list='+buy_items
        params += '&margin='+str(self.strat_margin_spinbox.value())
        params += '&refresh_interval='+str(self.strat_refresh_spinbox.value())
        params += '&balance_pct='+str(self.strat_bal_pct_spinbox.value())
        params += '&cex_list='+cex_items
        incompatible_coins = []
        if 'Binance' in cex_items:
            selected_coins = list(set(list(buy_list)+list(sell_list)))
            for coin in selected_coins:
                if coin not in coinslib.binance_coins:
                    incompatible_coins.append(coin)
        if len(incompatible_coins) > 0:
            resp = "The selected CEX "+str(cex_items)+" does not support "+str(incompatible_coins)+"!\n Please refine your selection..."
            QMessageBox.information(self, 'CEX Incompatible coins selected!', str(resp), QMessageBox.Ok, QMessageBox.Ok)
        else:
            logger.info('http://127.0.0.1:8000/strategies/create?'+params)
            resp = requests.post('http://127.0.0.1:8000/strategies/create?'+params).json()
            QMessageBox.information(self, 'Create Bot Strategy', str(resp), QMessageBox.Ok, QMessageBox.Ok)
        self.show_strategies_tab()

    def start_strat(self):
        selected_row = self.strategies_table.currentRow()
        if selected_row != -1 and self.strategies_table.item(selected_row,0) is not None:
            strategy_name = self.strategies_table.item(selected_row,0).text()
            resp = requests.post('http://127.0.0.1:8000/strategies/start/'+strategy_name).json()
            QMessageBox.information(self, 'Strategy '+strategy_name+' started', str(resp), QMessageBox.Ok, QMessageBox.Ok)
        else:
            resp = {
                "response": "error",
                "message": "No strategy row selected!"
            }
            QMessageBox.information(self, 'No strategy row selected!', str(resp), QMessageBox.Ok, QMessageBox.Ok)
        self.update_strategies_table()

    def stop_strat(self):
        selected_row = self.strategies_table.currentRow()
        if selected_row != -1 and self.strategies_table.item(selected_row,0) is not None:
            strategy_name = self.strategies_table.item(selected_row,0).text()
            resp = requests.post('http://127.0.0.1:8000/strategies/stop/'+strategy_name).json()
            QMessageBox.information(self, 'Strategy '+strategy_name+' stopped', str(resp), QMessageBox.Ok, QMessageBox.Ok)
        else:
            resp = {
                "response": "error",
                "message": "No strategy row selected!"
            }
            QMessageBox.information(self, 'Strategy stop error', str(resp), QMessageBox.Ok, QMessageBox.Ok)
        self.update_strategies_table()

    def stop_all_strats(self):
        resp = requests.post('http://127.0.0.1:8000/strategies/stop/all').json()

    def view_strat_session(self):
        selected_row = self.strat_summary_table.currentRow()
        if self.strat_summary_table.item(selected_row,1) is not None:
            session_num = self.strat_summary_table.item(selected_row,1).text()
            session_name = self.strat_summary_table.item(selected_row,0).text()
            session_info = requests.post('http://127.0.0.1:8000/strategies/session/'+session_name+'/'+session_num).json()
            result = ScrollMessageBox(session_info)
            result.exec_()

    def view_strat_summary(self):
        selected_row = self.strategies_table.currentRow()
        logger.info("Updating Strategy summary table")
        if selected_row != -1 and self.strategies_table.item(selected_row,0) is not None:
            strategy_name = self.strategies_table.item(selected_row,0).text()
            if self.summary_hide_empty_checkbox.isChecked():
                populate_table('', self.strat_summary_table, "", "", "4|0|EXCLUDE" ,"table/bot_strategy/summary/"+strategy_name)
            else:
                populate_table('', self.strat_summary_table, "", "", "",  "table/bot_strategy/summary/"+strategy_name)
            row_fg(self.strat_summary_table, QColor(218, 255, 127), 4, ['0'], 'exclude')

    def delete_strat(self):
        selected_row = self.strategies_table.currentRow()
        if selected_row != -1 and self.strategies_table.item(selected_row,0) is not None:
            strategy_name = self.strategies_table.item(selected_row,0).text()
            resp = requests.post('http://127.0.0.1:8000/strategies/delete/'+strategy_name).json()
        else:
            resp = {
                "response": "error",
                "message": "No strategy row selected!"
            }
        QMessageBox.information(self, 'Archive Bot Strategy', str(resp), QMessageBox.Ok, QMessageBox.Ok)
        self.update_strategies_table()

    ## HISTORY
    def mm2_view_swap(self):
        cancel = True
        selected_row = self.mm2_trades_table.currentRow()
        if self.mm2_trades_table.item(selected_row,10) is not None:
            swap_uuid = self.mm2_trades_table.item(selected_row,10).text()
            swap_info = rpclib.my_swap_status(self.creds[0], self.creds[1], swap_uuid).json()
            result = ScrollMessageBox(swap_info)
            result.exec_()

    ## CONFIG
    def set_localonly(self):
        # TODO: should this just be default, without remote option?
        local_only = self.checkbox_local_only.isChecked()
        if local_only:
            rpc_ip = '127.0.0.1'
            self.rpc_ip_text_input.setReadOnly(True)
            self.rpc_ip_text_input.setText(rpc_ip)
        else:
            self.rpc_ip_text_input.setReadOnly(False)

    def save_config(self):
        # update user config and credentials
        msg = ''
        gui = 'Makerbot v0.0.1'
        passphrase = self.seed_text_input.toPlainText()
        rpc_password = self.rpcpass_text_input.text()
        rpc_ip = self.rpc_ip_text_input.text()
        local_only = self.checkbox_local_only.isChecked()
        if local_only:
            rpc_ip = '127.0.0.1'
        ip_valid = guilib.validate_ip(rpc_ip)
        if not ip_valid:
            msg += 'RPC IP is invalid! \n'
        binance_key = self.binance_key_text_input.text()
        binance_secret = self.binance_secret_text_input.text()
        margin = float(self.creds[7])
        netid = self.netid_input.text()
        if passphrase == '':
            msg += 'No seed phrase input! \n'
        if rpc_password == '':
            msg += 'No RPC password input! \n'
        if rpc_ip == '':
            msg += 'No RPC IP input! \n'
        if msg == '':
            overwrite = True
            if os.path.isfile(config_path+self.username+"_MM2.enc"):
                confirm = QMessageBox.question(self, 'Confirm overwrite', "Existing settings detected. Overwrite?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if not confirm == QMessageBox.Yes:
                    overwrite = False
            if overwrite:

                passwd, ok = QInputDialog.getText(self, 'Enter Password', 'Enter your login password: ', QLineEdit.Password)
                if ok:
                    if passwd == self.password:
                        data = {}
                        data.update({"gui":gui})
                        data.update({"rpc_password":rpc_password})
                        data.update({"netid":int(netid)})
                        data.update({"passphrase":passphrase})
                        data.update({"userhome":home})
                        data.update({"rpc_local_only":local_only})
                        data.update({"rpc_allow_ip":rpc_ip})
                        data.update({"bn_key":binance_key})
                        data.update({"bn_secret":binance_secret})
                        data.update({"margin":margin})
                        data.update({"dbdir":config_path+"DB"})
                        # encrypt and store the config / credentials
                        enc_data = enc.encrypt_mm2_json(json.dumps(data), passwd)
                        with open(config_path+self.username+"_MM2.enc", 'w') as j:
                            j.write(bytes.decode(enc_data))
                        QMessageBox.information(self, 'Settings file created', "Settings updated. Please login again.", QMessageBox.Ok, QMessageBox.Ok)

                        logger.info("stop_mm2 with old creds")
                        try:
                            rpclib.stop_mm2(self.creds[0], self.creds[1])
                        except Exception as e:
                            logger.info("cache error")
                            logger.info(e)
                            pass
                        self.authenticated = False
                        self.show_login_tab()

                    else:
                        QMessageBox.information(self, 'Password incorrect!', 'Password incorrect!', QMessageBox.Ok, QMessageBox.Ok)
                        pass
        else:
            QMessageBox.information(self, 'Validation failed', msg, QMessageBox.Ok, QMessageBox.Ok)
            pass
    
    # Generate wallet seed
    # TODO: add other languages
    def generate_seed(self):
        seed_words_list = []
        while len(seed_words_list) < 24:
            word = random.choice(wordlist.wordlist)
            if word not in seed_words_list:
                seed_words_list.append(word)
        seed_phrase = " ".join(seed_words_list)
        self.seed_text_input.setText(seed_phrase)

    ## LOGS


    ### FUCTIONS TO REVIEW ###

    def start_bot_trading(self):
        buys = 0
        sells = 0
        for coin in self.buy_coins:
            if coin in coinslib.binance_coins and coin in self.active_coins:
                buys += 1
        for coin in self.sell_coins:
            if coin in coinslib.binance_coins and coin in self.active_coins:
                sells += 1
        if (buys == 1 and sells == 1 and buy_coins != sell_coins) or (buys > 0 and sells > 0):
            logger.info("starting bot")            
            self.bot_trade_thread = bot_trading_thread(self.creds, self.sell_coins, self.buy_coins, self.active_coins)
            self.bot_trade_thread.check_status.connect(self.check_mm_bot_order_swaps)
            self.bot_trade_thread.trigger.connect(self.update_bot_log)
            self.bot_trade_thread.start()
            self.bot_status_lbl.setText("ACTIVE")
            self.bot_status_lbl.setStyleSheet('color: #043409;\nbackground-color: rgb(166, 215, 166);')
            log_msg = get_time_str()+" Bot started"
            log_row = QListWidgetItem(log_msg)
            log_row.setForeground(QColor('#267F00'))
            #self.trading_logs_list.addItem(log_row)
        else:
            msg = 'Please activate at least one sell coin and at least one different buy coin (Binance compatible). '
            QMessageBox.information(self, 'Error', msg, QMessageBox.Ok, QMessageBox.Ok)
            self.setCurrentWidget(self.findChild(QWidget, 'tab_activate'))

    def update_bot_log(self, uuid, log_msg, log_result=''):
        log_row = QListWidgetItem(log_msg)
        log_row.setForeground(QColor('#00137F'))
        #self.trading_logs_list.addItem(log_row)
        if log_result != '':
            log_row = QListWidgetItem(">>> "+str(log_result))
            log_row.setForeground(QColor('#7F0000'))
            #self.trading_logs_list.addItem(log_row)

    def update_trading_log(self, sender, log_msg, log_result=''):
        timestamp = int(time.time())
        time_str = datetime.datetime.fromtimestamp(timestamp)
        prefix = str(time_str)+" ("+sender+"): "
        log_msg = prefix+log_msg
        log_row = QListWidgetItem(log_msg)
        log_row.setForeground(QColor('#00137F'))
        #self.trading_logs_list.addItem(log_row)
        if log_result != '':
            log_row = QListWidgetItem(">>> "+str(log_result))
            log_row.setForeground(QColor('#7F0000'))
            #self.trading_logs_list.addItem(log_row)

    def import_swap_data(self):
        swap_data = json.loads(self.import_swaps_input.toPlainText())
        resp = rpclib.import_swaps(self.creds[0], self.creds[1], swap_data).json()
        QMessageBox.information(self, 'Import Swap Data', str(resp), QMessageBox.Ok, QMessageBox.Ok)

    def recover_swap(self):
        uuid = self.swap_recover_uuid.text()
        resp = rpclib.recover_stuck_swap(self.creds[0], self.creds[1], uuid).json()
        QMessageBox.information(self, 'Recover Stuck Swap', str(resp), QMessageBox.Ok, QMessageBox.Ok)

    def update_prices_table(self):
        logger.info("Updating Prices table")
        populate_table('', self.prices_table, self.prices_table_msg, "", "", "table/prices")


    def update_mm2_trade_history_table(self):
        logger.info("Updating MM2 trade history table")
        if self.mm2_hide_failed_checkbox.isChecked():
            populate_table('', self.mm2_trades_table, self.mm2_trades_msg_lbl, "", "2|Failed|EXCLUDE","table/mm2_history")
        else:
            populate_table('', self.mm2_trades_table, self.mm2_trades_msg_lbl, "", "","table/mm2_history")
        if self.mm2_trades_table.rowCount() > 0:
            row_fg(self.mm2_trades_table, QColor(218, 255, 127), 2, ['Finished'], 'include')
            row_fg(self.mm2_trades_table, QColor(255, 127, 127), 2, ['Failed'], 'include')
            row_fg(self.mm2_trades_table, QColor(255, 233, 127), 2, ['Failed','Finished'], 'exclude')

    def update_strategy_history_table(self):
        logger.info("Updating Strategy history table")
        populate_table('', self.strategy_trades_table, self.strategy_trades_msg_lbl, "", "", "table/strategies_history")  
        row_fg(self.strategy_trades_table, QColor(218, 255, 127), 9, ['Complete'], 'include')
        row_fg(self.strategy_trades_table, QColor(255, 233, 127), 9, ['Complete'], 'exclude')

    # runs each time the tab is changed to populate the items on that tab
    def prepare_tab(self):
        try:
            self.active_coins = guilib.get_active_coins(self.creds[0], self.creds[1])
        except:
            # if not logged in, no creds
            pass
        QCoreApplication.processEvents()
        if self.authenticated:
            logger.info("authenticated")
            self.stacked_login.setCurrentIndex(1)
            index = self.currentIndex()
            if self.creds[0] == '':
                QMessageBox.information(self, 'Settings for user "'+self.username+'" not found!', "Settings not found. Please fill in the config form, save your settings and restart Antara Makerbot.", QMessageBox.Ok, QMessageBox.Ok)
                self.setCurrentWidget(self.findChild(QWidget, 'tab_config'))              
            elif index == 0:
                # activate
                logger.info('show_activation_tab')
                self.show_activation_tab()
            elif index == 1:
                # order book
                logger.info('show_mm2_orderbook_tab')
                self.show_mm2_orderbook_tab()
            elif index == 2:
                # binance acct
                logger.info('show_binance_tab')
                self.show_binance_trading_tab()
            elif index == 3:
                # wallet
                logger.info('show_mm2_wallet_tab')
                self.show_mm2_wallet_tab()
            elif index == 4:
                # strategies
                logger.info('show_strategies_tab')
                self.show_strategies_tab()
            elif index == 5:
                # Prices
                logger.info('show_prices_tab')
                self.show_prices_tab()
            elif index == 6:
                # history
                logger.info('show_history_tab')
                self.show_history_tab()
            elif index == 7:
                # config
                logger.info('show_config_tab')
                self.show_config_tab()
            elif index == 8:
                # logs
                logger.info('show_logs_tab')
                self.show_logs_tab()
        else:
            logger.info('show_activation_tab - login')
            self.stacked_login.setCurrentIndex(0)
            index = self.currentIndex()
            if index != 0:
                QMessageBox.information(self, 'Unauthorised access!', 'You must be logged in to access this tab', QMessageBox.Ok, QMessageBox.Ok)
            self.show_login_tab()

    # parse out user order uuids as a list
    def get_mm2_order_uuids(self):
        orders = rpclib.my_orders(self.creds[0], self.creds[1]).json()
        mm2_order_uuids = []
        if 'maker_orders' in orders['result']:
            maker_orders = orders['result']['maker_orders']
            for item in maker_orders:
                mm2_order_uuids.append(item)
        if 'taker_orders' in orders['result']:
            taker_orders = orders['result']['taker_orders']
            for item in taker_orders:
                mm2_order_uuids.append(item)
        return mm2_order_uuids

    def get_mm2_swap_events(self, events):
        event_types = []
        failed = False
        fail_event = False
        finished = False
        for event in events:
            event_types.append(event['event']['type'])
            if event['event']['type'] in rpclib.error_events: 
                failed = True
                fail_event = event['event']['type']
            if event['event']['type'] == 'Finished':
                finished = event['timestamp']
        return failed, fail_event, finished, event_types


if __name__ == '__main__':
    
    appctxt = ApplicationContext()
    screen_resolution = appctxt.app.desktop().screenGeometry()
    width, height = screen_resolution.width(), screen_resolution.height()
    logger.info("Screen width: "+str(width))
    logger.info("Screen height: "+str(height))
    window = Ui(appctxt)
    window.resize(width, height)
    exit_code = appctxt.app.exec_()
    if 'api_proc' in locals():
        logger.info("Kill api_proc")
        api_proc.kill()
        api_proc.wait()
        if platform.system() == 'Windows':
            kill_mm2 = subprocess.Popen(["tskill", "mmbot_api.exe"], startupinfo=startupinfo)
        else:
            kill_mm2 = subprocess.Popen(["pkill", "-9", "mmbot_api"], startupinfo=startupinfo)
        kill_mm2.wait()
    if 'mm2_proc' in locals():
        logger.info("Kill mm2_proc")
        mm2_proc.kill()
        mm2_proc.wait()
        if platform.system() == 'Windows':
            kill_mm2 = subprocess.Popen(["tskill", "mm2.exe"], startupinfo=startupinfo)
        else:
            kill_mm2 = subprocess.Popen(["pkill", "-9", "mm2"], startupinfo=startupinfo)
        kill_mm2.wait()
    sys.exit(exit_code)
