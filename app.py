from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from choose import StockChooser
import logging
from logging.handlers import RotatingFileHandler
import os

app = Flask(__name__, 
    static_url_path='',  # 这使得静态文件可以直接通过根路径访问
    static_folder='static'  # 简化路径配置
)
CORS(app)  # 启用跨域支持

# 创建logs目录（如果不存在）
if not os.path.exists('logs'):
    os.makedirs('logs')

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建文件处理器
file_handler = RotatingFileHandler(
    'logs/stockquant.log',
    maxBytes=1024*1024,  # 1MB
    backupCount=5,
    encoding='utf-8'
)
file_handler.setLevel(logging.INFO)

# 创建格式化器
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)

# 添加文件处理器到logger
logger.addHandler(file_handler)

# 同时输出到控制台
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# 创建 StockChooser 实例
chooser = StockChooser()

# 在 app.py 中添加调试信息
print("Current directory:", os.getcwd())
print("Static folder:", app.static_folder)
print("Static folder exists:", os.path.exists(app.static_folder))
print("Index.html exists:", os.path.exists(os.path.join(app.static_folder, 'index.html')))

@app.route('/')
def index():
    """返回主页"""
    return app.send_static_file('index.html')

@app.route('/api/stock/conditions', methods=['GET'])
def get_conditions():
    """获取当前选股条件"""
    try:
        return jsonify({
            'max_price': chooser.MAX_PRICE,
            'min_volume': chooser.MIN_VOLUME,
            'up_percent': chooser.UP_PERCENT
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stock/conditions', methods=['POST'])
def update_conditions():
    """更新选股条件"""
    try:
        data = request.json
        chooser.MAX_PRICE = float(data.get('max_price', chooser.MAX_PRICE))
        chooser.MIN_VOLUME = float(data.get('min_volume', chooser.MIN_VOLUME))
        chooser.UP_PERCENT = float(data.get('up_percent', chooser.UP_PERCENT))
        return jsonify({'message': '选股条件更新成功'})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/stock/scan', methods=['POST'])
def scan_stocks():
    """执行选股"""
    try:
        # 使用测试股票列表
        test_stocks = [
            'sz300616',  # 尚品宅配
            'sh600000',  # 浦发银行
            'sh601318',  # 中国平安
            'sz000001',  # 平安银行
            'sh600519',  # 贵州茅台
            'sz000858',  # 五粮液
            'sh601888',  # 中国中免
            'sz002594',  # 比亚迪
            'sz300750',  # 宁德时代
            'sh600036'   # 招商银行
        ]
        
        matched_stocks = []
        for stock_code in test_stocks:
            try:
                price_info = chooser.get_stock_data(stock_code)
                if chooser.check_stock_condition(price_info):
                    matched_stocks.append({
                        'code': stock_code,
                        'name': price_info['name'],
                        'price': price_info['price'],
                        'volume': price_info['volume'],
                        'amount': price_info['amount']
                    })
            except Exception as e:
                logger.error(f"处理股票 {stock_code} 时出错: {str(e)}")
                continue
                
        return jsonify({
            'status': 'success',
            'stocks': matched_stocks,
            'count': len(matched_stocks)
        })
        
    except Exception as e:
        logger.error(f"选股失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@app.route('/api/stock/query', methods=['GET'])
def query_stock():
    """查询单个股票信息"""
    try:
        stock_code = request.args.get('code', '')
        if not stock_code:
            return jsonify({
                'status': 'error',
                'message': '请输入股票代码'
            }), 400
            
        # 如果输入的是纯数字，自动添加交易所前缀
        if stock_code.isdigit():
            if stock_code.startswith('6'):
                stock_code = f'sh{stock_code}'
            else:
                stock_code = f'sz{stock_code}'
                
        logger.info(f"查询股票信息: {stock_code}")
        price_info = chooser.get_stock_data(stock_code)
        
        if not price_info:
            return jsonify({
                'status': 'error',
                'message': '未找到股票信息'
            }), 404
            
        return jsonify({
            'status': 'success',
            'data': {
                'code': stock_code,
                'name': price_info['name'],
                'price': price_info['price'],
                'volume': price_info['volume'],
                'amount': price_info['amount'],
                'change': (price_info['price'] - price_info['close']) / price_info['close'] * 100
            }
        })
        
    except Exception as e:
        logger.error(f"查询股票信息失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

if __name__ == '__main__':
    # 修改为监听所有网络接口，并显示详细日志
    print("Starting Flask server...")
    print("Please access: http://127.0.0.1:5000")
    app.run(host='0.0.0.0', port=5000, debug=True) 