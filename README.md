# StockQuant - 股票量化交易系统

这是一个基于Python的股票量化交易系统，包含数据获取、技术分析、策略回测和自动交易功能。

## 主要功能

1. **数据获取**：使用BaoStock和新浪财经API获取股票历史数据和实时行情
2. **技术分析**：计算常用技术指标（MA、MACD、RSI、KDJ等）
3. **策略回测**：回测交易策略的历史表现
4. **自动交易**：基于技术指标的自动交易系统

## 文件说明

- `auto_trade.py`: 自动交易脚本（需要pywin32和pywinauto）
- `auto_trade_no_gui.py`: 不依赖GUI的自动交易脚本（不需要pywin32和pywinauto）
- `test_stock_data.py`: 测试股票数据获取功能
- `test_baostock.py`: 测试BaoStock API连接
- `一年双回测的收益.py`: 策略回测脚本

## 安装依赖

```bash
pip install -r requirements.txt
```

## 常见问题解决

### pywin32 DLL加载失败

如果遇到pywin32 DLL加载失败的问题，可以尝试以下解决方案：

1. 重新安装pywin32：
```bash
pip uninstall pywin32
pip install pywin32
```

2. 运行修复脚本：
```bash
python fix_pywin32.py
```

3. 使用不依赖GUI的版本：
```bash
python auto_trade_no_gui.py
```

### BaoStock API错误

使用BaoStock API时，需要注意股票代码格式：

- BaoStock格式：`sh.600000`、`sz.300616`（带点）
- 新浪格式：`sh600000`、`sz300616`（不带点）

## 使用示例

### 测试股票数据获取

```bash
python test_stock_data.py
```

### 运行自动交易（模拟模式）

```bash
python auto_trade_no_gui.py
```

### 运行策略回测

```bash
python 一年双回测的收益.py
```

## 注意事项

1. 自动交易功能仅供学习和研究使用，不构成投资建议
2. 实盘交易前请充分测试策略
3. 请遵守相关法律法规和交易所规则

## 功能特点

- 多数据源支持
  - 新浪财经实时行情
  - 腾讯财经实时行情
  - 网易财经实时行情
  - TuShare Pro 数据接口
  - BaoStock 历史数据

- 实时行情监控
  - 支持实时获取股票价格、成交量等数据
  - 支持自定义股票代码监控
  - 支持沪深两市股票

- 消息通知
  - 钉钉机器人通知
  - 支持自定义消息模板
  - 实时推送股票数据

- 数据分析
  - K线数据获取
  - 历史数据分析
  - 技术指标计算

## 快速开始

1. 安装依赖

`Gary-Hertel`

请勿提交`issue`！可以加入交流群与其他朋友一起自学交流，加微信`mzjimmy`

------

## 一、配置文件的设置

**启动框架需要先导入必要的模块，并且载入一次配置文件！**

配置文件是一个`json`格式的文件`config.json`，在`docs`文件夹中有模板文件，其内容如下，将其中的信息替换成自己的即可：

```json
{
    "LOG": {
        "level": "debug",
        "handler": "stream"
    },
    "DINGTALK": "your dingding token",
    "TUSHARE": "your tushare token",
    "SENDMAIL": {
        "from": "your qq email address",
        "password": "your qq email authorization code",
        "to": "your qq email address",
        "server": "smtp.qq.com",
        "port": 587
    }
}
```

其中的内容说明：

+ `LOG`：日志配置
  + `level`：日志显示的等级，可选`debug`、`info`、`error`、`warning`、`critical`
  + `handler`：日志的输出方式，可选`stream`、`file`、`time`
+ `DINGTALK`：你的钉钉`webhook token`
+ `TUSHARE`：你的`tushare_pro token`
+ `SENDMAIL`：邮箱配置
  + `from`：发件邮箱，推荐使用`QQ`邮箱
  + `password`：你的`QQ`邮箱授权码，非`QQ`密码
  + `to`：收件邮箱，推荐使用`QQ`邮箱并在微信上绑定此邮箱以实现微信接收消息
  + `server`：邮箱服务器，`QQ`邮箱默认使用此服务器
  + `port`：邮箱端口，`QQ`邮箱默认此端口即可

除了配置的这些信息外，也可以向配置文件中添加任意的信息，但注意**不能与默认设置内容中大写的内容名称相同，即使你添加的信息是小写亦不可**！要在策略中使用向配置文件中增加的信息，示例如下：

> 比如我们向配置文件中添加一项信息
>
> ```json
> {
>     "LOG": {
>         "level": "debug",
>         "handler": "stream"
>     },
>     "DINGTALK": "your dingding token",
>     "TUSHARE": "your tushare token",
>     "SENDMAIL": {
>         "from": "your qq email address",
>         "password": "your qq email authorization code",
>         "to": "your qq email address",
>         "server": "smtp.qq.com",
>         "port": 587
>     },
>     "person_name": "Gary-Hertel"
> }
> ```
>
> 要在策略中使用，只需：
>
> ```python
> config.person_name
> ```



------

## 二、框架的启用

在我们配置好配置文件后，将其放入我们的项目中，接下来就可以使用我们的框架了：

```python
from stockquant.quant import *		# 导入必要的模块

config.loads('config.json')			# 载入配置文件
```



------

## 三、行情数据

行情数据获取，具体参数请看方法内部的说明文档，在开发工具中，按住`ctrl`用鼠标点击一下方法的名称即可查看。

| 说明                     |                           调用方式                           |
| :----------------------- | :----------------------------------------------------------: |
| 获取指定股票的实时数据   |                    `Market.tick(symbol)`                     |
| 获取深圳成指             |             `Market.shenzhen_component_index()`              |
| 获取上证综指             |             `Market.shanghai_component_index()`              |
| 获取历史k线数据          | `Market.kline(symbol, timeframe, adj=None, start_date=None, end_date=None)` |
| 股票列表                 |                `Market.stocks_list(day=None)`                |
| 查询今日沪深股市是否开盘 |                   `Market.today_is_open()`                   |
| 证券基本资料             |   `Market.stock_basic_info(symbol=None, symbol_name=None)`   |
| 查询除权除息信息         |        `Market.dividend_data(symbol, year, yearType)`        |
| 查询复权因子信息         | `Market.adjust_factor(symbol, start_date=None, end_date=None)` |
| 季频盈利能力             |    `Market.profit_data(symbol, year=None, quarter=None)`     |
| 季频营运能力             |   `Market.operation_data(symbol, year=None, quarter=None)`   |
| 季频成长能力             |    `Market.growth_data(symbol, year=None, quarter=None)`     |
| 季频偿债能力             |    `Market.balance_data(symbol, year=None, quarter=None)`    |
| 季频现金流量             |   `Market.cash_flow_data(symbol, year=None, quarter=None)`   |
| 季频杜邦指数             |    `Market.dupont_data(symbol, year=None, quarter=None)`     |
| 季频公司业绩快报         | `Market.performance_express_report(symbol, start_date, end_date)` |
| 季频公司业绩预告         |    `Market.forcast_report(symbol, start_date, end_date)`     |
| 存款利率                 |  `Market.deposit_rate_data(start_date=None, end_date=None)`  |
| 贷款利率                 |   `Market.loan_rate_data(start_date=None, end_date=None)`    |
| 存款准备金率             | `Market.required_reserve_ratio_data(start_date=None, end_date=None, yearType=None)` |
| 货币供应量               | `Market.money_supply_data_month(start_date=None, end_date=None)` |
| 货币供应量(年底余额)     | `Market.money_supply_data_year(start_date=None, end_date=None)` |
| 银行间同业拆放利率       |     `Market.shibor_data(start_date=None, end_date=None)`     |
| 获取行业分类信息         |       `Market.stock_industry(symbol=None, date=None)`        |
| 获取上证50成分股信息     |               `Market.sz50_stocks(date=None)`                |
| 沪深300成分股            |               `Market.hs300_stocks(date=None)`               |
| 中证500成分股            |               `Market.zz500_stocks(date=None)`               |
| 获取新股上市列表数据     |                     `Market.new_stock()`                     |

**Note: 获取指定股票的实时数据时，Tick对象数据结构如下：**

|        调用方式        | 数据类型 |  字段说明  |
| :--------------------: | :------: | :--------: |
|     `tick.symbol`      | `string` |  股票名称  |
|      `tick.last`       | `float`  |  当前价格  |
|      `tick.open`       | `float`  | 今日开盘价 |
|      `tick.high`       | `float`  | 今日最高价 |
|       `tick.low`       | `float`  | 今日最低价 |
| `tick.yesterday_close` | `float`  | 昨日收盘价 |
|    `tick.bid_price`    | `float`  |   竞买价   |
|    `tick.ask_price`    | `float`  |   竞卖价   |
|  `tick.transactions`   | `float`  |  成交数量  |
|    `tick.turnover`     | `float`  |  成交金额  |
|  `tick.bid1_quantity`  | `float`  |  买一数量  |
|   `tick.bid1_price`    | `float`  |  买一报价  |
|  `tick.bid2_quantity`  | `float`  |  买二数量  |
|   `tick.bid2_price`    | `float`  |  买二报价  |
|  `tick.bid3_quantity`  | `float`  |  买三数量  |
|   `tick.bid3_price`    | `float`  |  买三报价  |
|  `tick.bid4_quantity`  | `float`  |  买四数量  |
|   `tick.bid4_price`    | `float`  |  买四报价  |
|  `tick.bid5_quantity`  | `float`  |  买五数量  |
|   `tick.bid5_price`    | `float`  |  买五报价  |
|  `tick.ask1_quantity`  | `float`  |  卖一数量  |
|   `tick.ask1_price`    | `float`  |  卖一报价  |
|  `tick.ask2_quantity`  | `float`  |  卖二数量  |
|   `tick.ask2_price`    | `float`  |  卖二报价  |
|  `tick.ask3_quantity`  | `float`  |  卖三数量  |
|   `tick.ask3_price`    | `float`  |  卖三报价  |
|  `tick.ask4_quantity`  | `float`  |  卖四数量  |
|   `tick.ask4_price`    | `float`  |  卖四报价  |
|  `tick.ask5_quantity`  | `float`  |  卖五数量  |
|   `tick.ask5_price`    | `float`  |  卖五报价  |
|    `tick.timestamp`    |  `str`   |   时间戳   |



------



## 四、技术指标

```python
kline = Market.kline("sh601003", "1d")
```

|         指标名称         |               调用方式                |                            返回值                            |
| :----------------------: | :-----------------------------------: | :----------------------------------------------------------: |
|     `指数移动平均线`     |        `ATR(14, kline=kline)`         |                          `一维数组`                          |
|     `k线数据的长度`      |       `CurrentBar(kline=kline)`       |                          `整型数字`                          |
|          `布林`          |        `BOLL(20, kline=kline)`        | `{"upperband": 上轨， "middleband": 中轨， "lowerband": 下轨}` |
|        `顺势指标`        |        `CCI(20, kline=kline)`         |                          `一维数组`                          |
|       `周期最高价`       |      `HIGHEST(20, kline=kline)`       |                          `一维数组`                          |
|       `移动平均线`       |       `MA(20, 30, kline=kline)`       |                          `一维数组`                          |
|   `指数平滑异同平均线`   |    `MACD(14, 26, 9, kline=kline)`     |     `{'DIF': DIF数组, 'DEA': DEA数组, 'MACD': MACD数组}`     |
|       `指数平均数`       |      `EMA(20, 30, kline=kline)`       |                          `一维数组`                          |
| `