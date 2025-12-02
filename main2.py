import backtrader as bt
import pandas as pd
from datetime import datetime, timedelta

class HighestPointStrategy(bt.Strategy):
    params = (
        ('drop_threshold', 0.03),  # 下跌阈值 2%
        ('initial_investment', 10000),  # 初始投资金额
        ('additional_investment', 5000),  # 每次补仓金额
    )
    
    def __init__(self):
        self.highest_price = None  # 记录最高点价格
        self.last_buy_price = None  # 记录上次买入价格
        self.order = None
        self.cash_invested = 0  # 已投入现金总额
        
    def start(self):
        # 初始投资
        self.broker.set_cash(self.broker.get_cash() - self.params.initial_investment)
        self.cash_invested += self.params.initial_investment
        
        # 计算初始买入股数
        size = self.params.initial_investment / self.data.close[0]
        self.buy(size=size)
        
        # 设置初始最高点
        self.highest_price = self.data.close[0]
        self.last_buy_price = self.data.close[0]
        
        print(f"初始投资: {self.params.initial_investment:.2f}元, "
              f"价格: {self.data.close[0]:.2f}, "
              f"股数: {size:.2f}")
    
    def next(self):
        # 如果当前有订单未完成，则返回
        if self.order:
            return
            
        current_price = self.data.close[0]
        
        # 更新最高点
        if self.highest_price is None or current_price > self.highest_price:
            self.highest_price = current_price
        
        # 计算从最高点的下跌幅度
        if self.highest_price > 0:
            drop_percentage = (self.highest_price - current_price) / self.highest_price
            
            # 如果下跌超过阈值且现金充足，则补仓
            if (drop_percentage >= self.params.drop_threshold and 
                self.broker.get_cash() >= self.params.additional_investment):
                
                # 计算补仓股数
                size = self.params.additional_investment / current_price
                
                # 执行买入订单
                self.buy(size=size)
                self.cash_invested += self.params.additional_investment
                
                print(f"补仓投资: {self.params.additional_investment:.2f}元, "
                      f"当前价格: {current_price:.2f}, "
                      f"最高点: {self.highest_price:.2f}, "
                      f"下跌幅度: {drop_percentage*100:.2f}%, "
                      f"补仓股数: {size:.2f}")
                
                # 重置最高点为当前价格（从补仓后重新计算）
                self.highest_price = current_price
                self.last_buy_price = current_price
    
    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
            
        if order.status in [order.Completed]:
            if order.isbuy():
                print(f"买入完成 - 价格: {order.executed.price:.2f}, "
                      f"数量: {order.executed.size:.2f}, "
                      f"佣金: {order.executed.comm:.2f}")
            elif order.issell():
                print(f"卖出完成 - 价格: {order.executed.price:.2f}, "
                      f"数量: {order.executed.size:.2f}, "
                      f"佣金: {order.executed.comm:.2f}")
                
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            print(f"订单取消/保证金不足/被拒绝 - {order.status}")
            
        self.order = None

# 数据准备和回测执行
def run_backtest():
    # 创建Cerebro引擎
    cerebro = bt.Cerebro()
    
    # 添加策略
    cerebro.addstrategy(HighestPointStrategy)
    
    # 准备数据（使用您提供的数据处理代码）
    data = pd.read_csv("data.csv")
    data['datetime'] = pd.to_datetime(data['datetime'])
    one_year_ago = datetime.now() - timedelta(days=365*2)
    data = data[data['datetime'] >= one_year_ago]
    data = data.set_index('datetime')
    float_cols = ['open', 'high', 'low', 'close', "volume"]
    data[float_cols] = data[float_cols].apply(pd.to_numeric, downcast='float')
    
    # 创建数据feed
    data_feed = bt.feeds.PandasData(
        dataname=data,
        datetime=None,  # 使用索引作为datetime
        open='open',
        high='high',
        low='low',
        close='close',
        volume='volume',
        openinterest=None
    )
    
    # 添加数据
    cerebro.adddata(data_feed)
    
    # 设置初始资金
    cerebro.broker.set_cash(100000)
    
    # 设置佣金
    cerebro.broker.setcommission(commission=0)  # 0.1%佣金
    
    # 添加分析器
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    
    print('初始资金: %.2f' % cerebro.broker.getvalue())
    
    # 运行回测
    results = cerebro.run()
    
    # 打印结果
    strat = results[0]
    print('最终资金: %.2f' % cerebro.broker.getvalue())
    print('总投入资金: %.2f' % strat.cash_invested)
    print('夏普比率:', strat.analyzers.sharpe.get_analysis()['sharperatio'])
    print('最大回撤:', strat.analyzers.drawdown.get_analysis()['max']['drawdown'])
    print('收益率:', strat.analyzers.returns.get_analysis()['rtot'])
    
    # 绘制图表
    # cerebro.plot()

if __name__ == '__main__':
    run_backtest()