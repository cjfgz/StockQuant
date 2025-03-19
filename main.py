from utils.data_fetcher import fetch_data
from utils.visualizer import plot_trend
from strategies.moving_average_strategy import apply_moving_average_strategy
from models.regression_model import train_regression_model


def main():
    stock_code = "sh.600000"
    start_date = "2022-01-01"
    end_date = "2022-12-31"
    
    # 获取数据
    data = fetch_data(stock_code, start_date, end_date)
    
    # 可视化
    plot_trend(data)
    
    # 应用策略
    data = apply_moving_average_strategy(data)
    
    # 训练模型
    model = train_regression_model(data)
    
    # 打印模型系数
    print("Model Coefficients:", model.coef_)

if __name__ == "__main__":
    main() 