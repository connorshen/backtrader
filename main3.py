import backtrader as bt
import pandas as pd
from datetime import datetime, timedelta

class SmartStrategy(bt.Strategy):
    params = (
        ('drop_threshold', 0.02),  # 下跌阈值 3%
        ('additional_amount', 10000),  # 每次补仓金额
    )
    
    def __init__(self):
        self.base_buy_price = None  # 记录最高点价格
        self.order = None
    
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
                size = self.params.additional_amount / current_price
                self.order = self.buy(size=size)
                self.base_buy_price = current_price
                return
    
    def notify_order(self, order):
        current_date = self.data.datetime.date(0)
        
        if order.status in [order.Submitted, order.Accepted]:
            return
                
        if order.status in [order.Completed]:
            if order.isbuy():
                # 买入订单完成
                cost = order.executed.price * order.executed.size
                print(f"买入成功 - 日期: {current_date}, "
                      f"价格: {order.executed.price:.2f}, "
                      f"股数: {order.executed.size:.2f}, "
                      f"成本: {cost:.2f}元, "
                      f"剩余现金: {self.broker.get_cash():.2f}")
            elif order.issell():
                # 卖出订单完成
                revenue = order.executed.price * order.executed.size
                print(f"卖出成功 - 日期: {current_date}, "
                      f"价格: {order.executed.price:.2f}, "
                      f"股数: {order.executed.size:.2f}, "
                      f"收入: {revenue:.2f}元, "
                      f"剩余现金: {self.broker.get_cash():.2f}")
                
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            print(f"订单失败 - {order.status}, 日期: {current_date}")
            
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
    print(data.head())
    
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