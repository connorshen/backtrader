import backtrader as bt
import pandas as pd
from datetime import datetime, timedelta


class DeclineInvestingStrategy(bt.Strategy):
    params = (
        ('cash', 4000),  # 每次投资金额
        ('decline_threshold', 0.03),  # 下跌阈值 2%
        ('min_interval', 15),  # 最小投资间隔（交易日）
    )

    def __init__(self):
        self.order = None
        self.last_investment_price = None  # 上次投资时的价格
        self.peak_since_last_investment = None  # 上次投资后的最高点
        self.last_investment_date = None  # 上次投资日期
        self.investment_count = 0  # 记录投资次数
        self.total_invested = 0  # 记录总投资额
        self.decline_count = 0  # 记录触发下跌的次数

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                investment_amount = order.executed.size * order.executed.price
                self.investment_count += 1
                self.total_invested += investment_amount
                self.last_investment_price = order.executed.price
                self.peak_since_last_investment = order.executed.price
                self.last_investment_date = self.data.datetime.date(0)

                print(f"第{self.investment_count}次投资完成: "
                      f"日期={self.data.datetime.date(0)}, "
                      f"投入={investment_amount:.2f}, "
                      f"价格={order.executed.price:.2f}, "
                      f"购买数量={order.executed.size:.2f}, "
                      f"佣金={order.executed.comm:.2f}")

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            print(f'订单取消/保证金不足/被拒绝: {order.status}')

        self.order = None

    def next(self):
        # 如果已有订单 pending，不发出新订单
        if self.order:
            return

        current_price = self.data.close[0]
        current_date = self.data.datetime.date(0)

        # 初始化变量（第一次运行）
        if self.last_investment_price is None:
            self.last_investment_price = current_price
            self.peak_since_last_investment = current_price
            return

        if self.last_investment_date is None:
            self.last_investment_date = current_date
            return

        # 更新上次投资后的最高点
        if current_price > self.peak_since_last_investment:
            self.peak_since_last_investment = current_price

        # 计算下跌幅度
        decline_from_last_investment = (self.last_investment_price - current_price) / self.last_investment_price
        decline_from_peak = (self.peak_since_last_investment - current_price) / self.peak_since_last_investment

        # 检查是否满足下跌条件
        meets_decline_condition = (decline_from_last_investment >= self.p.decline_threshold or
                                   decline_from_peak >= self.p.decline_threshold)

        # 检查时间间隔条件
        days_since_last_investment = (current_date - self.last_investment_date).days
        meets_interval_condition = (days_since_last_investment >= self.p.min_interval)

        # 如果满足下跌条件且时间间隔足够，进行投资
        if meets_decline_condition and meets_interval_condition:
            cash_available = self.broker.getcash()
            investment_amount = min(self.p.cash, cash_available)

            if investment_amount > 0:
                size = investment_amount / current_price
                self.order = self.buy(size=size)
                self.decline_count += 1

                print(f"第{self.decline_count}次下跌触发投资: "
                      f"日期={current_date}, "
                      f"距离上次投资={days_since_last_investment}天, "
                      f"当前价格={current_price:.2f}, "
                      f"较上次投资下跌={decline_from_last_investment * 100:.2f}%, "
                      f"较最高点下跌={decline_from_peak * 100:.2f}%, "
                      f"投资金额={investment_amount:.2f}")

    def stop(self):
        # 回测结束时打印总结
        total_value = self.broker.getvalue()
        initial_cash = 100000
        total_return = (total_value - initial_cash) / initial_cash * 100

        print("\n===== 逢跌定投策略总结 =====")
        print(f"总触发下跌次数: {self.decline_count}")
        print(f"总投资次数: {self.investment_count}")
        print(f"总投资金额: {self.total_invested:.2f}")
        print(f"最终投资组合价值: {total_value:.2f}")
        print(f"剩余现金: {self.broker.getcash():.2f}")
        print(f"总收益率: {total_return:.2f}%")

        # 计算年化收益率
        years = len(self.data) / 252
        if years > 0:
            annual_return = (total_value / initial_cash) ** (1 / years) - 1
            print(f"年化收益率: {annual_return * 100:.2f}%")


# 获取数据（保持原有数据获取逻辑）
data = pd.read_csv("data.csv")
data['datetime'] = pd.to_datetime(data['datetime'])
one_year_ago = datetime.now() - timedelta(days=365*4)
data = data[data['datetime'] >= one_year_ago]
data = data.set_index('datetime')
float_cols = ['open', 'high', 'low', 'close', "volume"]
data[float_cols] = data[float_cols].apply(pd.to_numeric, downcast='float')

# 创建Backtrader数据
bt_data = bt.feeds.PandasData(dataname=data)

# 运行回测
cerebro = bt.Cerebro()
cerebro.broker.set_coc(True)
cerebro.addstrategy(DeclineInvestingStrategy)
cerebro.broker.setcash(100000.0)
cerebro.adddata(bt_data)
cerebro.broker.setcommission(commission=0.0)

print('初始投资组合价值: %.2f' % cerebro.broker.getvalue())
cerebro.run()
print('最终投资组合价值: %.2f' % cerebro.broker.getvalue())
cerebro.plot()