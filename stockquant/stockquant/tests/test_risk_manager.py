import unittest
import pandas as pd
import numpy as np
from datetime import datetime
from trade.risk_manager import RiskManager

class TestRiskManager(unittest.TestCase):
    def setUp(self):
        """测试前的准备工作"""
        self.risk_manager = RiskManager()
        
        # 模拟投资组合
        self.portfolio = {
            'sh.600000': {
                'code': 'sh.600000',
                'name': '浦发银行',
                'industry': '银行',
                'shares': 1000,
                'cost': 10.0,
                'current_price': 11.0,
                'weight': 0.2
            },
            'sh.601318': {
                'code': 'sh.601318',
                'name': '中国平安',
                'industry': '保险',
                'shares': 500,
                'cost': 40.0,
                'current_price': 42.0,
                'weight': 0.3
            }
        }
        
        # 模拟股票数据
        self.stock_data = pd.DataFrame({
            'date': pd.date_range(start='2024-01-01', periods=20),
            'open': np.random.uniform(10, 12, 20),
            'high': np.random.uniform(11, 13, 20),
            'low': np.random.uniform(9, 11, 20),
            'close': np.random.uniform(10, 12, 20),
            'volume': np.random.uniform(100000, 200000, 20)
        })
        
    def test_position_limit(self):
        """测试持仓限制"""
        # 测试持仓数量限制
        result = self.risk_manager.check_position_limit(self.portfolio)
        self.assertTrue(result)
        
        # 添加更多持仓直到超过限制
        for i in range(10):
            self.portfolio[f'test_stock_{i}'] = {
                'weight': 0.05
            }
        result = self.risk_manager.check_position_limit(self.portfolio)
        self.assertFalse(result)
        
    def test_industry_limit(self):
        """测试行业持仓限制"""
        result = self.risk_manager.check_industry_limit(self.portfolio, '银行')
        self.assertTrue(result)
        
        # 添加更多银行股直到超过行业限制
        self.portfolio['sh.600015'] = {
            'industry': '银行',
            'weight': 0.3
        }
        result = self.risk_manager.check_industry_limit(self.portfolio, '银行')
        self.assertFalse(result)
        
    def test_stock_risk(self):
        """测试股票风险检查"""
        result = self.risk_manager.check_stock_risk(self.stock_data)
        self.assertTrue(result)
        
        # 测试成交量过低的情况
        low_volume_data = self.stock_data.copy()
        low_volume_data['volume'] = 1000
        result = self.risk_manager.check_stock_risk(low_volume_data)
        self.assertFalse(result)
        
    def test_stop_loss(self):
        """测试止损功能"""
        # 正常情况
        position = {
            'cost': 10.0,
            'current_price': 9.8  # 2% 跌幅，未触发止损
        }
        result = self.risk_manager.check_stop_loss(position)
        self.assertFalse(result)
        
        # 触发止损
        position['current_price'] = 9.0  # 10% 跌幅
        result = self.risk_manager.check_stop_loss(position)
        self.assertTrue(result)
        
    def test_stop_profit(self):
        """测试止盈功能"""
        # 正常情况
        position = {
            'cost': 10.0,
            'current_price': 11.0  # 10% 涨幅，未触发止盈
        }
        result = self.risk_manager.check_stop_profit(position)
        self.assertFalse(result)
        
        # 触发止盈
        position['current_price'] = 12.0  # 20% 涨幅
        result = self.risk_manager.check_stop_profit(position)
        self.assertTrue(result)
        
    def test_portfolio_risk(self):
        """测试组合风险计算"""
        risk_metrics = self.risk_manager.calculate_portfolio_risk(self.portfolio)
        
        self.assertIsNotNone(risk_metrics)
        self.assertTrue('total_value' in risk_metrics)
        self.assertTrue('total_profit' in risk_metrics)
        self.assertTrue('max_drawdown' in risk_metrics)
        self.assertTrue('volatility' in risk_metrics)
        self.assertTrue('sharpe_ratio' in risk_metrics)
        
    def test_risk_report(self):
        """测试风险报告生成"""
        report = self.risk_manager.generate_risk_report(self.portfolio)
        
        self.assertIsNotNone(report)
        self.assertIsInstance(report, str)
        self.assertTrue('风险评估报告' in report)
        self.assertTrue('组合总市值' in report)
        self.assertTrue('总收益率' in report)
        
    def test_update_params(self):
        """测试参数更新"""
        new_params = {
            'stop_loss': 0.08,
            'stop_profit': 0.20
        }
        self.risk_manager.update_params(new_params)
        
        self.assertEqual(self.risk_manager.params['stop_loss'], 0.08)
        self.assertEqual(self.risk_manager.params['stop_profit'], 0.20)
        
if __name__ == '__main__':
    unittest.main() 