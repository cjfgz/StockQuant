import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

def plot_trend(data, column='close'):
    data[column] = pd.to_numeric(data[column], errors='coerce')  # 确保数据为数值类型
    plt.figure(figsize=(10, 6))
    sns.lineplot(x='date', y=column, data=data)
    plt.title(f'Stock {column.capitalize()} Trend')
    plt.xlabel('Date')
    plt.ylabel(column.capitalize())
    plt.show() 