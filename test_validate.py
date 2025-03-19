import pandas as pd
import numpy as np

# 创建一个模拟的股票数据框
def create_test_df():
    data = {
        'date': ['2025-03-01', '2025-03-02', '2025-03-03', '2025-03-04', '2025-03-05'],
        'code': ['sh.600000', 'sh.600000', 'sh.600000', 'sh.600000', 'sh.600000'],
        'open': ['10.1', '10.2', '10.3', '10.4', '10.5'],
        'high': ['10.5', '10.6', '10.7', '10.8', '10.9'],
        'low': ['9.9', '10.0', '10.1', '10.2', '10.3'],
        'close': ['10.2', '10.3', '10.4', '10.5', '10.6'],
        'volume': ['1000000', '1100000', '1200000', '1300000', '1400000'],
        'amount': ['10200000', '11330000', '12480000', '13650000', '14840000'],
        'turn': ['1.5', '1.6', '1.7', '1.8', '1.9'],
        'pctChg': ['1.0', '0.98', '0.97', '0.96', '0.95']
    }
    return pd.DataFrame(data)

# 测试数据类型转换
def test_data_conversion():
    df = create_test_df()
    
    print("原始数据框:")
    print(df.head())
    print("\n原始数据类型:")
    print(df.dtypes)
    
    # 转换数据类型
    numeric_cols = ['close', 'open', 'high', 'low', 'volume', 'amount', 'turn', 'pctChg']
    for col in numeric_cols:
        if col in df.columns:
            print(f"\n转换前 {col} 的数据类型: {df[col].dtype}")
            print(f"转换前 {col} 的示例值: {df[col].iloc[0]}")
            
            # 转换数据类型
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
            print(f"转换后 {col} 的数据类型: {df[col].dtype}")
            print(f"转换后 {col} 的示例值: {df[col].iloc[0]}")
    
    # 测试比较操作
    for col in ['close', 'volume']:
        print(f"\n测试比较: {col} <= 0")
        print(f"{col} 的类型: {type(df[col])}")
        print(f"{col} 的第一个值: {df[col].iloc[0]}, 类型: {type(df[col].iloc[0])}")
        
        try:
            # 执行比较
            has_non_positive = (df[col] <= 0).any()
            print(f"比较结果: {has_non_positive}")
        except Exception as e:
            print(f"比较时出错: {str(e)}")

if __name__ == "__main__":
    test_data_conversion() 