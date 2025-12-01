import backtrader as bt
import pandas as pd
from datetime import datetime, timedelta


class DollarCostAveraging(bt.Strategy):
    params = (
        ('cash', 10000),  # 每次定投金额
    )

    def __init__(self):
        self.order = None
        self.last_month = -1  # 记录上次交易的月份
        self.investment_count = 0  # 记录定投次数
        self.total_invested = 0  # 记录总投资额

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # 订单已提交/被接受 - 什么都不做
            return

        if order.status in [order.Completed]:
            # 订单已完成
            if order.isbuy():
                # 买入订单完成
                investment_amount = order.executed.size * order.executed.price
                self.investment_count += 1
                self.total_invested += investment_amount

                print(f"第{self.investment_count}次定投完成: "
                      f"日期={self.data.datetime.date(0)}, "
                      f"投入={investment_amount:.2f}, "
                      f"价格={order.executed.price:.2f}, "
                      f"购买数量={order.executed.size:.2f}, "
                      f"佣金={order.executed.comm:.2f}")

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            # 订单被取消/保证金不足/被拒绝
            print(f'订单取消/保证金不足/被拒绝: {order.status}')

        # 重置订单
        self.order = None

    def next(self):
        # 如果已有订单 pending，不发出新订单
        if self.order:
            return

        # 获取当前日期
        current_date = self.data.datetime.date(0)
        current_month = current_date.month

        # 检查月份是否变化（每月第一个交易日执行定投）
        if current_month != self.last_month:
            # 计算可购买的数量
            cash_available = self.broker.getcash()
            investment_amount = min(self.p.cash, cash_available)

            if investment_amount > 0:
                # 计算购买数量
                size = investment_amount / self.data.close[0]
                # 发出买入订单
                self.order = self.buy(size=size)

                print(f"发出第{self.investment_count + 1}次定投订单: "
                      f"日期={current_date}, "
                      f"计划投入={investment_amount:.2f}, "
                      f"当前价格={self.data.close[0]:.2f}")

            self.last_month = current_month

    def stop(self):
        # 回测结束时打印总结
        total_value = self.broker.getvalue()
        total_return = (total_value - 100000) / 100000 * 100

        print("\n===== 定投总结 =====")
        print(f"总定投次数: {self.investment_count}")
        print(f"总投资金额: {self.total_invested:.2f}")
        print(f"最终投资组合价值: {total_value:.2f}")
        print(f"剩余现金: {self.broker.getcash():.2f}")
        print(f"总收益率: {total_return:.2f}%")

        # 计算年化收益率
        years = len(self.data) / 252  # 假设一年有252个交易日
        if years > 0:
            annual_return = (total_value / 100000) ** (1 / years) - 1
            print(f"年化收益率: {annual_return * 100:.2f}%")

# 获取数据
data = pd.read_csv("data.csv")
data['datetime'] = pd.to_datetime(data['datetime'])
one_year_ago = datetime.now() - timedelta(days=365 * 3)
data = data[data['datetime'] >= one_year_ago]
data = data.set_index('datetime')
float_cols = ['open', 'high', 'low', 'close', "volume"]
data[float_cols] = data[float_cols].apply(pd.to_numeric, downcast='float')

# 创建Backtrader数据
bt_data = bt.feeds.PandasData(dataname=data)

# 运行回测
cerebro = bt.Cerebro()
cerebro.broker.set_coc(True)
cerebro.addstrategy(DollarCostAveraging)
cerebro.broker.setcash(100000.0)
cerebro.adddata(bt_data)
cerebro.broker.setcommission(commission=0.0)

print('初始投资组合价值: %.2f' % cerebro.broker.getvalue())
cerebro.run()
print('最终投资组合价值: %.2f' % cerebro.broker.getvalue())
cerebro.plot()
