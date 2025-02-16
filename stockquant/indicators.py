import pandas as pd
import numpy as np

# 在导入 pandas_ta 之前添加一个兼容层
if not hasattr(np, 'NaN'):
    np.NaN = np.nan

import pandas_ta as ta


def ATR(df, timeperiod=14):
    """
    ATR指标
    :param df: 数据帧
    :param timeperiod: 长度参数
    :return: 返回一个一维数组
    """
    return df.ta.atr(length=timeperiod)


def BOLL(df, timeperiod=20):
    """
    布林带
    :param df: 数据帧
    :param timeperiod: 长度参数
    :return: 返回一个字典 {"upperband": 上轨数组， "middleband": 中轨数组， "lowerband": 下轨数组}
    """
    result = df.ta.bbands(length=timeperiod)
    upperband = result['BBANDS_upper']
    middleband = result['BBANDS_middle']
    lowerband = result['BBANDS_lower']
    dict = {"upperband": upperband, "middleband": middleband, "lowerband": lowerband}
    return dict


def CCI(df, timeperiod=14):
    """
    CCI指标
    :param df: 数据帧
    :param timeperiod: 长度参数
    :return:
    """
    return df.ta.cci(length=timeperiod)


def CurrentBar(df):
    """
    获取k线数据的长度
    :param df: 数据帧
    :return: 返回一个整型数字
    """
    return len(df)


def HIGHEST(df, timeperiod=30):
    """
    最高值
    :param df: 数据帧
    :param timeperiod: 长度参数
    :return:返回一个一维数组
    """
    return df.rolling(window=timeperiod).max()


def MA(df, timeperiod=5):
    """
    移动平均线
    :param df: 数据帧
    :param timeperiod: 长度参数
    :return: 返回一个一维数组
    """
    return df.ta.sma(length=timeperiod)


def MACD(df, fastperiod=12, slowperiod=26, signalperiod=9):
    """
    MACD指标
    :param df: 数据帧
    :param fastperiod: 参数1
    :param slowperiod: 参数2
    :param signalperiod: 参数3
    :return: 返回一个字典 {'DIF': DIF数组, 'DEA': DEA数组, 'MACD': MACD数组}
    """
    macd = df.ta.macd(fast=fastperiod, slow=slowperiod, signal=signalperiod)
    return macd


def EMA(df, timeperiod=30):
    """
    指数移动平均线
    :param df: 数据帧
    :param timeperiod: 长度参数
    :return: 返回一个一维数组
    """
    return df.ta.ema(length=timeperiod)


def KAMA(df, timeperiod=30):
    """
    适应性移动平均线
    :param df: 数据帧
    :param timeperiod: 长度参数
    :return: 返回一个一维数组
    """
    return df.ta.kama(length=timeperiod)


def KDJ(df, fastk_period=9, slowk_period=3, slowd_period=3):
    """
    KDJ指标
    :param df: 数据帧
    :param fastk_period: 参数1
    :param slowk_period: 参数2
    :param slowd_period: 参数3
    :return: 返回一个字典，{'k': k值数组， 'd': d值数组}
    """
    kdj = df.ta.stoch(k=fastk_period, d=slowk_period, smooth_d=slowd_period)
    return kdj


def LOWEST(df, timeperiod=30):
    """
    最低值
    :param df: 数据帧
    :param timeperiod: 长度参数
    :return: 返回一个一维数组
    """
    return df.rolling(window=timeperiod).min()


def OBV(df):
    """
    OBV
    :param df: 数据帧
    :return: 返回一个一维数组
    """
    return df.ta.obv()


def RSI(df, timeperiod=14):
    """
    RSI指标
    :param df: 数据帧
    :param timeperiod: 长度参数
    :return:返回一个一维数组
    """
    return df.ta.rsi(length=timeperiod)


def ROC(df, timeperiod=10):
    """
    变动率指标
    :param df: 数据帧
    :param timeperiod: 长度参数
    :return:返回一个一维数组
    """
    return df.ta.roc(length=timeperiod)


def STOCHRSI(df, timeperiod=14, fastk_period=5, fastd_period=3):
    """
    随机RSI
    :param df: 数据帧
    :param timeperiod: 参数1
    :param fastk_period:参数2
    :param fastd_period:参数3
    :return: 返回一个字典  {'STOCHRSI': STOCHRSI数组, 'fastk': fastk数组}
    """
    result = df.ta.stochrsi(length=timeperiod, rsi_length=fastk_period, k=fastd_period)
    STOCHRSI = result['STOCHRSI']
    fastk = ta.sma(STOCHRSI, length=3)
    dict = {'stochrsi': STOCHRSI, 'fastk': fastk}
    return dict


def SAR(df, acceleration=0.02, maximum=0.2):
    """
    抛物线指标
    :param df: 数据帧
    :param acceleration: 加速参数
    :param maximum: 最大参数
    :return: 返回一个一维数组
    """
    return df.ta.psar(acceleration=acceleration, maximum=maximum)


def STDDEV(df, timeperiod=5):
    """
    标准差
    :param df: 数据帧
    :param timeperiod: 周期参数
    :return: 返回一个一维数组
    """
    return df.rolling(window=timeperiod).std()


def TRIX(df, timeperiod=30):
    """
    三重指数平滑平均线
    :param df: 数据帧
    :param timeperiod: 长度参数
    :return:返回一个一维数组
    """
    return df.ta.trix(length=timeperiod)


def VOLUME():
    """
    成交量
    :return: 返回一个一维数组
    """
    pass