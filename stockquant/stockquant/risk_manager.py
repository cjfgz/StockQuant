import logging
import pandas as pd
import numpy as np
from datetime import datetime

class RiskManager:
    def __init__(self, config=None):
        """初始化风险管理器"""
        self.setup_logging()
        self.setup_params(config)
        
    def setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/risk_manager.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def setup_params(self, config):
        """设置风险控制参数"""
        self.params = {
            'max_position': 0.3,      # 单个股票最大持仓比例
            'total_position': 0.8,    # 总持仓上限
            'stop_loss': 0.05,        # 止损比例
            'stop_profit': 0.15,      # 止盈比例
            'max_drawdown': 0.2,      # 最大回撤限制
            'risk_free_rate': 0.03,   # 无风险利率
            'position_limit': 10,      # 最大持仓数量
            'industry_limit': 0.4,    # 单一行业持仓上限
            'min_volume': 100000,     # 最小成交量要求
            'max_price': 100,         # 最高价格限制
            'volatility_limit': 0.3   # 波动率上限
        }
        
        if config:
            self.params.update(config)
            
    def check_position_limit(self, portfolio):
        """检查持仓限制"""
        try:
            # 检查持仓数量
            if len(portfolio) >= self.params['position_limit']:
                self.logger.warning("已达到最大持仓数量限制")
                return False
                
            # 计算总持仓比例
            total_position = sum(pos['weight'] for pos in portfolio.values())
            if total_position >= self.params['total_position']:
                self.logger.warning("已达到总持仓上限")
                return False
                
            return True
            
        except Exception as e:
            self.logger.error(f"检查持仓限制时出错: {str(e)}")
            return False
            
    def check_industry_limit(self, portfolio, industry):
        """检查行业持仓限制"""
        try:
            # 计算行业持仓比例
            industry_position = sum(
                pos['weight'] for pos in portfolio.values() 
                if pos['industry'] == industry
            )
            
            if industry_position >= self.params['industry_limit']:
                self.logger.warning(f"行业 {industry} 已达到持仓上限")
                return False
                
            return True
            
        except Exception as e:
            self.logger.error(f"检查行业持仓限制时出错: {str(e)}")
            return False
            
    def check_stock_risk(self, stock_data):
        """检查单个股票的风险"""
        try:
            if stock_data is None or len(stock_data) < 20:
                return False
                
            latest = stock_data.iloc[-1]
            
            # 检查成交量
            if latest['volume'] < self.params['min_volume']:
                self.logger.warning("成交量过低")
                return False
                
            # 检查价格
            if latest['close'] > self.params['max_price']:
                self.logger.warning("股价过高")
                return False
                
            # 检查波动率
            volatility = stock_data['close'].pct_change().std()
            if volatility > self.params['volatility_limit']:
                self.logger.warning("波动率过高")
                return False
                
            return True
            
        except Exception as e:
            self.logger.error(f"检查股票风险时出错: {str(e)}")
            return False
            
    def calculate_position_size(self, portfolio, stock_code, price):
        """计算开仓数量"""
        try:
            # 计算当前总持仓市值
            total_value = sum(
                pos['shares'] * pos['current_price'] 
                for pos in portfolio.values()
            )
            
            # 计算可用资金
            available_cash = total_value * (1 - sum(
                pos['weight'] for pos in portfolio.values()
            ))
            
            # 计算目标持仓市值
            target_value = min(
                available_cash,
                total_value * self.params['max_position']
            )
            
            # 计算股数（向下取整到100的倍数）
            shares = int(target_value / price / 100) * 100
            
            return shares
            
        except Exception as e:
            self.logger.error(f"计算开仓数量时出错: {str(e)}")
            return 0
            
    def check_stop_loss(self, position):
        """检查止损条件"""
        try:
            if position['current_price'] <= position['cost'] * (1 - self.params['stop_loss']):
                self.logger.warning(f"触发止损: 成本价 {position['cost']:.2f}, 当前价 {position['current_price']:.2f}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"检查止损条件时出错: {str(e)}")
            return False
            
    def check_stop_profit(self, position):
        """检查止盈条件"""
        try:
            if position['current_price'] >= position['cost'] * (1 + self.params['stop_profit']):
                self.logger.info(f"触发止盈: 成本价 {position['cost']:.2f}, 当前价 {position['current_price']:.2f}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"检查止盈条件时出错: {str(e)}")
            return False
            
    def calculate_portfolio_risk(self, portfolio):
        """计算组合风险指标"""
        try:
            if not portfolio:
                return {
                    'total_value': 0,
                    'total_profit': 0,
                    'max_drawdown': 0,
                    'volatility': 0,
                    'sharpe_ratio': 0
                }
                
            # 计算总市值和收益
            total_value = sum(pos['shares'] * pos['current_price'] for pos in portfolio.values())
            total_cost = sum(pos['shares'] * pos['cost'] for pos in portfolio.values())
            total_profit = (total_value - total_cost) / total_cost
            
            # 计算历史最大回撤
            values = pd.Series([pos['current_price'] * pos['shares'] for pos in portfolio.values()])
            rolling_max = values.expanding().max()
            drawdowns = values / rolling_max - 1
            max_drawdown = drawdowns.min()
            
            # 计算波动率
            returns = pd.Series([
                (pos['current_price'] - pos['cost']) / pos['cost'] 
                for pos in portfolio.values()
            ])
            volatility = returns.std()
            
            # 计算夏普比率
            excess_returns = returns - self.params['risk_free_rate']
            sharpe_ratio = np.sqrt(252) * excess_returns.mean() / volatility if volatility != 0 else 0
            
            return {
                'total_value': total_value,
                'total_profit': total_profit,
                'max_drawdown': max_drawdown,
                'volatility': volatility,
                'sharpe_ratio': sharpe_ratio
            }
            
        except Exception as e:
            self.logger.error(f"计算组合风险指标时出错: {str(e)}")
            return None
            
    def update_params(self, new_params):
        """更新风险控制参数"""
        try:
            for key, value in new_params.items():
                if key in self.params:
                    self.params[key] = value
            self.logger.info("风险控制参数已更新")
        except Exception as e:
            self.logger.error(f"更新风险控制参数时出错: {str(e)}")
            
    def generate_risk_report(self, portfolio):
        """生成风险报告"""
        try:
            risk_metrics = self.calculate_portfolio_risk(portfolio)
            if not risk_metrics:
                return "无法生成风险报告：计算风险指标失败"
                
            report = f"""
风险评估报告 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
--------------------------------
组合总市值: {risk_metrics['total_value']:,.2f}
总收益率: {risk_metrics['total_profit']*100:.2f}%
最大回撤: {risk_metrics['max_drawdown']*100:.2f}%
组合波动率: {risk_metrics['volatility']*100:.2f}%
夏普比率: {risk_metrics['sharpe_ratio']:.2f}

持仓分析:
持仓数量: {len(portfolio)}
单个持仓上限: {self.params['max_position']*100}%
总持仓上限: {self.params['total_position']*100}%

风险控制参数:
止损线: {self.params['stop_loss']*100}%
止盈线: {self.params['stop_profit']*100}%
波动率上限: {self.params['volatility_limit']*100}%
--------------------------------
"""
            return report
            
        except Exception as e:
            self.logger.error(f"生成风险报告时出错: {str(e)}")
            return "生成风险报告失败" 