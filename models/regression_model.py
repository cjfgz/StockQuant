from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression

def train_regression_model(data):
    X = data[['open', 'high', 'low', 'volume']]
    y = data['close']
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    model = LinearRegression()
    model.fit(X_train, y_train)
    return model 