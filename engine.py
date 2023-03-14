from binance.client import Client
from binance import ThreadedWebsocketManager
from binance.enums import *
from binance.exceptions import BinanceAPIException, BinanceOrderException
from binance.helpers import round_step_size
import requests
import time
import numpy as np

client = Client(api_key=binance_api_key, api_secret=binance_api_secret)

print("Client initialized")

%matplotlib inline

import socketio
from IPython import display
from IPython.display import clear_output
import numpy as np
import matplotlib.pyplot as plt
import datetime as dt
from dateutil.relativedelta import relativedelta
import time
import requests
import json
import os
import sys
import csv

# SOCKETIO RECEIVER - /!\ INTERFACE IT TO THE ORDER EXECUTION SERVICE (ConnectTrade)

sio = socketio.Client()

key = 'YOUR SOCKET IO KEY'

@sio.event
def connect():
    print('connection established')
    #sio.emit("buy_signal", {'key': key , 'stratname': 'Py Strategy', 'pair': 'BTCUSDT'})

@sio.event
def message(data):
    print('Message received: ', data)

@sio.event
def disconnect():
    print('disconnected from server')
    
@sio.event
def buy_signal(data):
    print('Buy signal received ', data)
    # {'stratid': '1017', 'stratname': '', 'pair': 'BTCUSDT', 'price': '39984.62000000', 'new': True, 'score': 'NA'}
    print("Strategy: ", data["stratname"])
    print("Pair: ", data["pair"])
    
@sio.event
def sell_signal(data):
    print('Sell signal received ', data)
    # {'stratid': '1017', 'stratname': '', 'pair': 'BTCUSDT', 'price': '40138.96000000', 'new': True, 'score': 'NA'}
    print("Strategy: ", data["stratname"])
    print("Pair: ", data["pair"])

sio.connect("YOUR SOCKET IO NAME"+key)


import datetime
import time
import os
import math
import pandas as pd
import numpy as np

################################### UI TRADING DASHBOARD WIDGETS ###################################

real_trading_enabled = True
execution_on = True
history_pnl = []

import ipywidgets as widgets
from ipywidgets import interact, interact_manual, GridspecLayout

toggle = widgets.Button(description='Live trading disabled', button_style='success')
toggle1 = widgets.Button(description='Pause execution', button_style='info')
toggle2 = widgets.Button(description='Update values', button_style='info')
toggle3 = widgets.Button(description='Close all trades', button_style='info')
#display(widgets.HTML(value="<h2>IDTS Isolated Margin Trading Manager</h2>"))
display(widgets.HTML(value="<h1>Trading dashboard</h1>"))
#e2 = widgets.FloatText(value=10,description='ALT Quantity:',disabled=True)
#display(toggle, toggle1, toggle2)
# create a 10x2 grid layout
#grid1 = GridspecLayout(1, 2, width="100%")
# fill it in with widgets
#grid1[0, 0] = e2
# set the widget properties
#grid1[:, 0].layout.height = 'auto'
#display(grid1)
# create a 10x2 grid layout
grid = GridspecLayout(1, 4, width="100%")
# fill it in with widgets
grid[0, 0] = toggle
grid[0, 1] = toggle1
grid[0, 2] = toggle2
grid[0, 3] = toggle3
# set the widget properties
grid[:, 0].layout.height = 'auto'
display(grid)
display(widgets.Label(description="Current position"))
display(widgets.HTML(value="<h1>Live trades PNL</h1>"))

def trade_button_status(b):
    global real_trading_enabled
    
    if(real_trading_enabled == False):
        real_trading_enabled = True
        b.description = 'Live trading enabled'
        b.button_style = 'warning'
    elif(real_trading_enabled == True):
        real_trading_enabled = False
        b.description = 'Live trading disabled'
        b.button_style = 'success'
    # what happens when we press the button
    print('Live trading status changed: ', real_trading_enabled)

toggle.on_click(trade_button_status)

def update_execution_status(b):
    global execution_on
    
    if(execution_on == True):
        real_trading_enabled = False
        b.description = 'Resume execution'
        b.button_style = 'warning'
    elif(execution_on == False):
        real_trading_enabled = True
        b.description = 'Pause execution'
        b.button_style = 'info'
    # what happens when we press the button
    print('Live execution status updated: ', execution_on)

toggle1.on_click(update_execution_status)

out = widgets.Output()

display(out)

def update_array_disp():
    global history_pnl
    
    df = pd.DataFrame(history_pnl, columns = ['Pair','Position','Type','Quantity'])
    
    with out:
        out.clear_output()
        display(df.iloc[::-1].tail(1000))
    return out

#history_pnl.append([25, 22, 3 ,10, 0])
#history_pnl.append([25, 22, 3 ,23, 0])

display(widgets.HTML(value="<h1>Logs</h1>"))

################################### BINANCE ORDERS BRIDGE ###################################

from binance.client import Client
from binance import ThreadedWebsocketManager
from binance.enums import *
from binance.exceptions import BinanceAPIException, BinanceOrderException
from binance.helpers import round_step_size
import requests

# /!\ REAL ACCOUNT WITH KYC
binance_api_key = 'REDACTED'    #Enter your own API-key here
binance_api_secret = 'REDACTED' #Enter your own API-secret here

client = Client(api_key=binance_api_key, api_secret=binance_api_secret)

print("Client initialized")

# SETUP:
# Isolated Margin:
# ------------------------
# USDT: QTY + 10% FEES (110usdt)
# TOKEN: 10% FEES      (10usdt)
# -> QTY IN ALT for trade

trade_protect = []

def save_positions():
    global trade_protect
    global history_pnl
    
    %store trade_protect
    %store history_pnl
    
def restore_positions():
    global trade_protect
    global history_pnl
    
    %store -r trade_protect
    %store -r history_pnl
    
# --------  BINANCE POSITION MAKER  ---------

lotsize = {
    "FETUSDT": 1.00000000,
    "VTHOUSDT": 1.00000000,
    "SOLUSDT": 0.01000000
}

def binance_open_long(pair):
    global trade_protect
    
    # Protection: check if a trade is already open
    if str(pair)+"OPENLONG" in trade_protect:
        print("A trade is already open")
        return
    if str(pair)+"OPENSHORT" in trade_protect:
        print("A trade is already open")
        return
    
    print("[BINANCE] OPEN LONG ",pair)
    try:
        if(real_trading_enabled == True):
            
            # Get available USDT
            qty = np.multiply(float(client.get_isolated_margin_account(symbols=pair)['assets'][0]['quoteAsset']['free']),0.95)
            # Get price
            price = float(requests.get('https://api.binance.com/api/v1/ticker/price?symbol='+pair).json()['price'])
            # Round
            qty = round_step_size(np.divide(qty,price), lotsize[pair])
            print("QTY: ", qty)

            order = client.create_margin_order(
                symbol=pair,
                quantity=qty,
                isIsolated='TRUE',
                side='BUY',
                sideEffectType = 'MARGIN_BUY',
                type='MARKET')
            
        else:
            print("virtual")
        
        trade_protect.append(str(pair)+"OPENLONG")
        history_pnl.append([pair, "LONG", "OPEN" , qty])
        save_positions()
    except BinanceAPIException as e:
        print(e)
    except BinanceOrderException as e:
        print(e)
        
def binance_close_long(pair):
    global trade_protect
    
    # Protection: check if a trade is already open
    if str(pair)+"OPENLONG" in trade_protect:
        pass
    else:
        print("No long trade open")
        return
    
    print("[BINANCE] CLOSE LONG ",pair)
    try:
        if(real_trading_enabled == True):

            # Get available BASE
            qty = np.multiply(float(client.get_isolated_margin_account(symbols=pair)['assets'][0]['baseAsset']['free']),0.95)
            # Round
            qty = round_step_size(qty, lotsize[pair])
            print("QTY: ", qty)

            order = client.create_margin_order(
                symbol=pair,
                quantity=qty,
                isIsolated='TRUE',
                side='SELL',
                sideEffectType = 'AUTO_REPAY',
                type='MARKET')
            
        else:
            print("virtual")
            
        trade_protect.remove(str(pair)+"OPENLONG")
        history_pnl.append([pair, "LONG", "CLOSE" , qty])
        save_positions()
    except BinanceAPIException as e:
        print(e)
    except BinanceOrderException as e:
        print(e)
        
def binance_open_short(pair, qty):
    global trade_protect
    
    # Protection: check if a trade is already open
    if str(pair)+"OPENLONG" in trade_protect:
        print("A trade is already open")
        return
    if str(pair)+"OPENSHORT" in trade_protect:
        print("A trade is already open")
        return
    
    # BORROW ALT, SELL ALT
    print("[BINANCE] OPEN SHORT ",pair)
    try:
        if(real_trading_enabled == True):

            # Get available USDT
            qty = np.multiply(float(client.get_isolated_margin_account(symbols=pair)['assets'][0]['quoteAsset']['free']),0.95)
            # Get price
            price = float(requests.get('https://api.binance.com/api/v1/ticker/price?symbol='+pair).json()['price'])
            # Round
            qty = round_step_size(np.divide(qty,price), lotsize[pair])
            print("QTY: ", qty)

            loan = client.create_margin_loan(asset=pair[:-4], symbol=pair, isIsolated='TRUE', amount=qty)
            order = client.create_margin_order(
                symbol=pair,
                quantity=qty,
                isIsolated='TRUE',
                side='SELL',
                sideEffectType = 'MARGIN_BUY',
                type='MARKET')
            
        else:
            print("virtual")
            
        trade_protect.append(str(pair)+"OPENSHORT")
        history_pnl.append([pair, "SHORT", "OPEN" , qty])
        save_positions()
    except BinanceAPIException as e:
        print(e)
    except BinanceOrderException as e:
        print(e)
        
def binance_close_short(pair, qty):
    global trade_protect
    
    # Protection: check if a trade is already open
    if str(pair)+"OPENSHORT" in trade_protect:
        pass
    else:
        print("No short trade open")
        return
    
    
    # BUY ALT, REPAY IN ALT
    print("[BINANCE] CLOSE SHORT ",pair)
    try:
        if(real_trading_enabled == True):

            # Get available USDT
            acc = client.get_isolated_margin_account(symbols=pair)['assets'][0]['baseAsset']
            qty = float(acc['borrowed'])+float(acc['interest'])
            print(qty)
            # Round
            qty = round_step_size(qty, lotsize[pair])
            print("QTY: ", qty)

            order = client.create_margin_order(
                symbol=pair,
                quantity=qty,
                isIsolated='TRUE',
                side='BUY',
                sideEffectType = 'AUTO_REPAY',
                type='MARKET')
            
        else:
            print("virtual")
            
        trade_protect.remove(str(pair)+"OPENSHORT")
        history_pnl.append([pair, "SHORT", "CLOSE" , qty])
        save_positions()
    except BinanceAPIException as e:
        print(e)
    except BinanceOrderException as e:
        print(e)

################################### BINANCE BENCHMARK ###################################

s = time.time()
#binance_open_long("FETUSDT", 15)
delai = time.time()-s
print('delai: ',delai)

s = time.time()
#binance_close_long("FETUSDT", 15)
delai = time.time()-s
print('delai: ',delai)

s = time.time()
#binance_open_short("FETUSDT", 15)
delai = time.time()-s
print('delai: ',delai)

s = time.time()
#binance_close_short("FETUSDT", 15)
delai = time.time()-s
print('delai: ',delai)

################################### CONNECTION WITH STRATEGY ###################################

import threading

restore_positions()

# Restore positions manually
# binance_close_long("FETUSDT")

print(time.time())
qty = np.multiply(float(client.get_isolated_margin_account(symbols="BTCUSDT")['assets'][0]['baseAsset']['free']),0.95)
print(time.time())

#Initializing connection
ConnectTrade = []
%store ConnectTrade

while(False):

    #print("loop")
    %store -r ConnectTrade

    if(len(ConnectTrade) == 3):
        #print(time.time())
        print("Received: ", ConnectTrade)

        # Trading order processing

        t_pair = ConnectTrade[0]
        t_pos  = ConnectTrade[1]
        t_type = ConnectTrade[2]

        # Find qty
        # FET qty = 1500
        # VTHO qty = 1

        print(t_pair)

        # Make trade
        if(t_pos == "LONG" and t_type == "OPEN" ):
            binance_open_long(t_pair)
        if(t_pos == "LONG" and t_type == "CLOSE" ):
            binance_close_long(t_pair)
        if(t_pos == "SHORT" and t_type == "OPEN" ):
            binance_open_short(t_pair)
        if(t_pos == "SHORT" and t_type == "CLOSE" ):
            binance_close_short(t_pair)

        update_array_disp()
        #print(history_pnl)

        ConnectTrade = []
        %store ConnectTrade

    time.sleep(.3)
    

    


################################### EXECUTION ENGINE END ###################################
