#!/usr/bin/env python3
import os
from os.path import expanduser
import time
import json
import hmac
import hashlib
import requests
import sys
from urllib.parse import urljoin, urlencode

# Get and set config
cwd = os.getcwd()
home = expanduser("~")

# from https://code.luasoftware.com/tutorials/cryptocurrency/python-connect-to-binance-api/

base_url = 'https://api.binance.com'

class BinanceException(Exception):
    def __init__(self, status_code, data):
        self.status_code = status_code
        if data:
            self.code = data['code']
            self.msg = data['msg']
        else:
            self.code = None
            self.msg = None
        message = f"{status_code} [{self.code}] {self.msg}"
        super().__init__(message)

def get_serverTime():
    path =  '/api/v1/time'
    params = None

    timestamp = int(time.time() * 1000)

    url = urljoin(base_url, path)
    r = requests.get(url, params=params)
    if r.status_code == 200:
        # print(json.dumps(r.json(), indent=2))
        data = r.json()
        print(f"diff={timestamp - data['serverTime']}ms")
    else:
        raise BinanceException(status_code=r.status_code, data=r.json())

def get_price(api_key, ticker_pair):
    path = '/api/v3/ticker/price'
    headers = {
        'X-MBX-APIKEY': api_key
    }
    params = {
        'symbol': ticker_pair
    }
    url = urljoin(base_url, path)
    r = requests.get(url, headers=headers, params=params)
    return r.json()

def get_orderbook(api_key, ticker_pair):
    path = '/api/v1/depth'
    headers = {
        'X-MBX-APIKEY': api_key
    }
    params = {
        'symbol': ticker_pair,
        'limit': 5
    }
    url = urljoin(base_url, path)
    r = requests.get(url, headers=headers, params=params)
    if r.status_code == 200:
        return r.json()
    else:
        raise BinanceException(status_code=r.status_code, data=r.json())


def create_buy_order(api_key, api_secret, ticker_pair, qty, price):
    path = '/api/v3/order'
    timestamp = int(time.time() * 1000)
    headers = {
        'X-MBX-APIKEY': api_key
    }
    params = {
        'symbol': ticker_pair,
        'side': 'BUY',
        'type': 'LIMIT',
        'timeInForce': 'GTC',
        'quantity': qty,
        'price': price,
        'recvWindow': 5000,
        'timestamp': timestamp
    }

    query_string = urlencode(params)
    params['signature'] = hmac.new(api_secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()

    url = urljoin(base_url, path)
    r = requests.post(url, headers=headers, params=params)
    if r.status_code == 200:
        data = r.json()
        print(json.dumps(data, indent=2))
    else:
        raise BinanceException(status_code=r.status_code, data=r.json())

def create_sell_order(api_key, api_secret, ticker_pair, qty, price):
    print("Selling "+str(qty)+" "+ticker_pair+" at "+str(price))
    path = '/api/v3/order'
    timestamp = int(time.time() * 1000)
    headers = {
        'X-MBX-APIKEY': api_key
    }
    params = {
        'symbol': ticker_pair,
        'side': 'SELL',
        'type': 'LIMIT',
        'timeInForce': 'GTC',
        'quantity': qty,
        'price': price,
        'recvWindow': 5000,
        'timestamp': timestamp
    }
    query_string = urlencode(params)
    params['signature'] = hmac.new(api_secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
    url = urljoin(base_url, path)
    r = requests.post(url, headers=headers, params=params)
    if r.status_code == 200:
        data = r.json()
        print(json.dumps(data, indent=2))
    else:
        raise BinanceException(status_code=r.status_code, data=r.json())

def get_account_info(api_key, api_secret):
    path = '/api/v3/account'
    timestamp = int(time.time() * 1000)
    headers = {
        'X-MBX-APIKEY': api_key
    }
    params = {
        'recvWindow': 5000,
        'timestamp': timestamp
    }
    query_string = urlencode(params)
    params['signature'] = hmac.new(api_secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
    url = urljoin(base_url, path)
    r = requests.get(url, headers=headers, params=params)
    return r.json()

def get_order(api_key, api_secret, ticker_pair, order_id):
    path = '/api/v3/order'
    timestamp = int(time.time() * 1000)
    headers = {
        'X-MBX-APIKEY': api_key
    }
    params = {
        'symbol': ticker_pair,
        'orderId': order_id,
        'recvWindow': 5000,
        'timestamp': timestamp
    }
    query_string = urlencode(params)
    params['signature'] = hmac.new(api_secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()

    url = urljoin(base_url, path)
    r = requests.get(url, headers=headers, params=params)
    if r.status_code == 200:
        data = r.json()
        print(json.dumps(data, indent=2))
    else:
        raise BinanceException(status_code=r.status_code, data=r.json())

def delete_order(api_key, api_secret, ticker_pair, order_id):
    path = '/api/v3/order'
    timestamp = int(time.time() * 1000)
    headers = {
        'X-MBX-APIKEY': api_key
    }
    params = {
        'symbol': ticker_pair,
        'orderId': order_id,
        'recvWindow': 5000,
        'timestamp': timestamp
    }

    query_string = urlencode(params)
    params['signature'] = hmac.new(api_secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()

    url = urljoin(base_url, path)
    r = requests.delete(url, headers=headers, params=params)
    if r.status_code == 200:
        data = r.json()
        print(json.dumps(data, indent=2))
    else:
        raise BinanceException(status_code=r.status_code, data=r.json())

def get_deposit_addr(api_key, api_secret, asset):
    path = '/wapi/v3/depositAddress.html'
    timestamp = int(time.time() * 1000)
    headers = {
        'X-MBX-APIKEY': api_key
    }
    params = {
        'asset': asset,
        'timestamp': timestamp
    }
    query_string = urlencode(params)
    params['signature'] = hmac.new(api_secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
    url = urljoin(base_url, path)
    r = requests.get(url, headers=headers, params=params)
    return r.json()

def withdraw(api_key, api_secret, asset, addr, amount):
    path = '/wapi/v3/withdraw.html'
    timestamp = int(time.time() * 1000)
    headers = {
        'X-MBX-APIKEY': api_key
    }
    params = {
        'asset': asset,
        'address': addr,
        'amount': amount,
        'timestamp': timestamp
    }
    query_string = urlencode(params)
    params['signature'] = hmac.new(api_secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
    url = urljoin(base_url, path)
    r = requests.post(url, headers=headers, params=params)
    return r.json()

def round_to_step(coin, qty, stepSize):
    # check https://api.binance.com/api/v1/exchangeInfo for stepsize for coin
    #Under Symbols Filters LOT_SIZE
    return int(float(qty)/float(stepSize))*float(stepSize)
