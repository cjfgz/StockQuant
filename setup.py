# -*- coding:utf-8 -*-

from setuptools import setup, find_packages


setup(
    name="stockquant",
    version="0.1",
    packages=find_packages(),
    platforms="any",
    description="Professional quant framework",
    url="https://github.com/Gary-Hertel/StockQuant",
    author="Gary-Hertel",
    author_email="garyhertel@foxmail.com",
    license="MIT",
    keywords=[
        "stockquant", "quant", "framework"
    ],
    install_requires=[
        "pandas",
        "numpy",
        "requests",
        "concurrent-log-handler",
        "colorlog",
        "matplotlib",
        "tushare",
        "baostock",
        "easytrader"
    ]
)