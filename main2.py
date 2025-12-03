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
        self.total_shares = 0  # 总持股数量
        self.total_investments = 0  # 总投资次数
        
    def start(self):
        # 初始投资
        initial_cash = self.params.initial_investment
        self.broker.set_cash(self.broker.get_cash() - initial_cash)
        self.cash_invested += initial_cash
        
        # 计算初始买入股数
        price = self.data.close[0]
        size = initial_cash / price
        self.buy(size=size)
        
        # 设置初始最高点
        self.highest_price = price
        self.last_buy_price = price
        self.total_shares = size
        self.total_investments = 1
        
        print(f"初始投资: {initial_cash:.2f}元, "
              f"价格: {price:.2f}, "
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
                self.order = self.buy(size=size)
                self.cash_invested += self.params.additional_investment
                
                print(f"触发补仓条件 - 当前价格: {current_price:.2f}, "
                      f"最高点: {self.highest_price:.2f}, "
                      f"下跌幅度: {drop_percentage*100:.2f}%")
                
                # 重置最高点为当前价格（从补仓后重新计算）
                self.highest_price = current_price
                self.last_buy_price = current_price
    
    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
            
        if order.status in [order.Completed]:
            if order.isbuy():
                # 更新总持股数量
                self.total_shares += order.executed.size
                self.total_investments += 1
                
                # 计算持仓收益
                current_value = self.total_shares * order.executed.price
                invested_value = self.cash_invested
                unrealized_pnl = current_value - invested_value
                pnl_percentage = (unrealized_pnl / invested_value) * 100 if invested_value > 0 else 0
                
                print(f"\n=== 第{self.total_investments}次投资 ===")
                print(f"买入完成 - 价格: {order.executed.price:.2f}, "
                      f"数量: {order.executed.size:.2f}, "
                      f"金额: {order.executed.price * order.executed.size:.2f}")
                print(f"总持股: {self.total_shares:.2f}")
                print(f"总投资: {self.cash_invested:.2f}")
                print(f"持仓市值: {current_value:.2f}")
                print(f"持仓收益: {unrealized_pnl:+.2f} ({pnl_percentage:+.2f}%)")
                print(f"剩余现金: {self.broker.get_cash():.2f}")
                print(f"账户总值: {self.broker.getvalue():.2f}")
                print("=" * 50)
                
            elif order.issell():
                print(f"卖出完成 - 价格: {order.executed.price:.2f}, "
                      f"数量: {order.executed.size:.2f}, "
                      f"佣金: {order.executed.comm:.2f}")
                
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            print(f"订单取消/保证金不足/被拒绝 - {order.status}")
            
        self.order = None
    
    def stop(self):
        # 最终持仓收益计算
        current_value = self.total_shares * self.data.close[0]
        final_unrealized_pnl = current_value - self.cash_invested
        final_pnl_percentage = (final_unrealized_pnl / self.cash_invested) * 100 if self.cash_invested > 0 else 0
        
        print("\n" + "="*80)
        print("回测结束 - 最终持仓收益汇总")
        print("="*80)
        print(f"总投资次数: {self.total_investments}")
        print(f"总投入资金: {self.cash_invested:.2f}")
        print(f"总持股数量: {self.total_shares:.2f}")
        print(f"最终股价: {self.data.close[0]:.2f}")
        print(f"持仓市值: {current_value:.2f}")
        print(f"最终持仓收益: {final_unrealized_pnl:+.2f} ({final_pnl_percentage:+.2f}%)")
        print(f"剩余现金: {self.broker.get_cash():.2f}")
        print(f"账户总值: {self.broker.getvalue():.2f}")

# 数据准备和回测执行
def run_backtest():
    # 创建Cerebro引擎
    cerebro = bt.Cerebro()
    cerebro.broker.set_coc(True)
    
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
        dataname=data
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
    cerebro.plot()

if __name__ == '__main__':
    run_backtest()