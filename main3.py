import backtrader as bt
import pandas as pd
from datetime import datetime, timedelta

class SmartStrategy(bt.Strategy):
    params = (
        ('drop_threshold', 0.03),  # 下跌阈值 3%
        ('initial_amount', 5000),  # 初始投资金额
        ('additional_amount', 5000),  # 每次补仓金额
    )
    
    def __init__(self):
        self.base_buy_price = None  # 记录最高点价格
        self.order = None
        
    def start(self):
        # 初始投资
        initial_cash = self.params.initial_amount
        self.broker.set_cash(self.broker.get_cash() - initial_cash)
        
        # 计算初始买入股数
        current_price = self.data.close[0]
        size = initial_cash / current_price
        self.buy(size=size)
        
        # 设置初始最高点和买入后最低点
        self.base_buy_price = current_price
        current_date = self.data.datetime.date(0) 
        
        print(f"初始投资: {initial_cash:.2f}元, "
              f"日期: {current_date}, "
              f"价格: {current_price:.2f}, "
              f"股数: {size:.2f}")
    
    def next(self):
        # 如果当前有订单未完成，则返回
        if self.order:
            return
            
        current_price = self.data.close[0]
        current_date = self.data.datetime.date(0) 
        
        # 更新最高点（用于下跌判断）
        if self.base_buy_price is None or current_price > self.base_buy_price:
            self.base_buy_price = current_price
        
        # 1. 下跌补仓逻辑
        if self.base_buy_price > 0:
            drop_percentage = (self.base_buy_price - current_price) / self.base_buy_price
            
            # 如果下跌超过阈值且现金充足，则补仓
            if (drop_percentage >= self.params.drop_threshold and 
                self.broker.get_cash() >= self.params.additional_amount):
                
                # 计算补仓股数
                size = self.params.additional_amount / current_price
                
                # 执行买入订单
                self.order = self.buy(size=size)
                
                print(f"触发补仓条件 - 当前价格: {current_price:.2f}, "
                      f"日期: {current_date}, "
                      f"最高点: {self.base_buy_price:.2f}, "
                      f"下跌幅度: {drop_percentage*100:.2f}%")
                self.base_buy_price = current_price
                return
    
    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
                
        if order.status in [order.Canceled, order.Margin, order.Rejected]:
            print(f"订单被拒绝 - {order.status}")
            
        self.order = None

# 数据准备和回测执行
def run_backtest():
    # 创建Cerebro引擎
    cerebro = bt.Cerebro()
    
    # 添加策略
    cerebro.addstrategy(SmartStrategy)
    
    # 准备数据（使用您提供的数据处理代码）
    data = pd.read_csv("data.csv")
    data['datetime'] = pd.to_datetime(data['datetime'])
    one_year_ago = datetime.now() - timedelta(days=365*1)
    data = data[data['datetime'] >= one_year_ago]
    data = data.set_index('datetime')
    float_cols = ['open', 'high', 'low', 'close', "volume"]
    data[float_cols] = data[float_cols].apply(pd.to_numeric, downcast='float')
    
    # 创建数据feed
    data_feed = bt.feeds.PandasData(
        dataname=data
    )
    
    # 添加数据
    cerebro.adddata(data_feed)
    cerebro.broker.set_coc(True)
    # 设置初始资金
    cerebro.broker.set_cash(100000)
    
    print('初始投资组合价值: %.2f' % cerebro.broker.getvalue())
    cerebro.run()
    print('最终投资组合价值: %.2f' % cerebro.broker.getvalue())
    cerebro.plot()

if __name__ == '__main__':
    run_backtest()