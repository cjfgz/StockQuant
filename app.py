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

@app.route('/api/stock/conditions', methods=['GET'])
def get_conditions():
    """获取当前选股条件"""
    return jsonify({
        'max_price': chooser.MAX_PRICE,
        'min_volume': chooser.MIN_VOLUME,
        'up_percent': chooser.UP_PERCENT,
        'min_turnover': chooser.MIN_TURNOVER,
        'min_circ_mv': chooser.MIN_CIRC_MV,
        'max_circ_mv': chooser.MAX_CIRC_MV
    })

@app.route('/api/stock/conditions', methods=['POST'])
def update_conditions():
    """更新选股条件"""
    try:
        data = request.json
        chooser.MAX_PRICE = float(data.get('max_price', chooser.MAX_PRICE))
        chooser.MIN_VOLUME = float(data.get('min_volume', chooser.MIN_VOLUME))
        chooser.UP_PERCENT = float(data.get('up_percent', chooser.UP_PERCENT))
        chooser.MIN_TURNOVER = float(data.get('min_turnover', chooser.MIN_TURNOVER))
        chooser.MIN_CIRC_MV = float(data.get('min_circ_mv', chooser.MIN_CIRC_MV))
        chooser.MAX_CIRC_MV = float(data.get('max_circ_mv', chooser.MAX_CIRC_MV))
        return jsonify({'message': '选股条件更新成功'})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/stock/scan', methods=['POST'])
def scan_stocks():
    """执行选股"""
    try:
        logger.info("开始执行选股...")
        matched_stocks = []
        
        # 获取股票列表并排除ST股
        logger.info("正在获取股票列表...")
        df = chooser.pro.stock_basic(
            exchange='', 
            list_status='L', 
            fields='ts_code,symbol,name'
        )
        
        if df.empty:
            logger.error("获取股票列表失败")
            return jsonify({
                'status': 'error',
                'message': '获取股票列表失败'
            }), 500
            
        total_stocks = len(df)
        logger.info(f"共获取到 {total_stocks} 只股票")
        
        # 遍历股票列表进行筛选
        processed = 0
        for _, row in df.iterrows():
            processed += 1
            if processed % 100 == 0:  # 每处理100只股票记录一次进度
                logger.info(f"已处理 {processed}/{total_stocks} 只股票")
                
            if 'ST' in row['name']:
                continue  # 排除ST股票
                
            prefix = 'sh' if row['ts_code'].endswith('.SH') else 'sz'
            stock_code = f"{prefix}{row['symbol']}"
            
            try:
                # 获取股票数据
                price_info = chooser.get_stock_data(stock_code)
                if chooser.check_stock_condition(price_info):
                    logger.info(f"找到符合条件的股票: {stock_code} {price_info['name']}")
                    matched_stocks.append({
                        'code': stock_code,
                        'name': price_info['name'],
                        'price': price_info['price'],
                        'volume': price_info['volume'],
                        'turnover': price_info['turnover_rate'],
                        'circ_mv': price_info['circ_mv']
                    })
            except Exception as e:
                logger.error(f"处理股票 {stock_code} 时出错: {str(e)}")
                continue

        logger.info(f"选股完成，共找到 {len(matched_stocks)} 只符合条件的股票")
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
                'turnover': price_info['turnover_rate'],
                'circ_mv': price_info['circ_mv'],
                'change': (price_info['price'] - price_info['close']) / price_info['close'] * 100
            }
        })
        
    except Exception as e:
        logger.error(f"查询股票信息失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

# 修改根路由处理
@app.route('/')
def index():
    return app.send_static_file('index.html')

if __name__ == '__main__':
    app.run(debug=True, port=5000) 