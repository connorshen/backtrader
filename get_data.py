import pandas as pd
import akshare as ak
from datetime import datetime
data = ak.fund_etf_hist_em(symbol="512890", period="daily", start_date="20140101", end_date=datetime.now().strftime("%Y%m%d"), adjust="qfq")
print(data.columns)
data = data.iloc[:, :6]
data.columns = ['datetime', 'open', 'high', 'low', 'close', 'volume']
data['datetime'] = pd.to_datetime(data['datetime'])
data['datetime'] = data['datetime'] + pd.Timedelta(hours=9, minutes=30)
data = data.set_index('datetime')
data.to_csv("data.csv")