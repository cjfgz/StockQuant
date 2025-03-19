def apply_moving_average_strategy(data):
    data['MA5'] = data['close'].rolling(window=5).mean()
    data['MA10'] = data['close'].rolling(window=10).mean()
    data['Signal'] = 0
    data['Signal'][data['MA5'] > data['MA10']] = 1
    return data 