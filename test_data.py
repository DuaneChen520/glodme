
import pandas as pd
import numpy as np
import akshare as ak
from datetime import datetime, timedelta
import logging
from typing import Optional, Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MobileDataFetcher:
    def __init__(self, ticker: str = "518880"):
        self.ticker = ticker

    def get_realtime_quote(self) -> Dict[str, Any]:
        try:
            df = ak.stock_zh_a_spot_em(symbol=self.ticker)
            if not df.empty:
                return {
                    'status': 'success',
                    'data_source': 'akshare_em',
                    'price': float(df['最新价'].iloc[0]),
                    'change': float(df['涨跌额'].iloc[0]) if pd.notna(df['涨跌额'].iloc[0]) else 0,
                    'change_pct': float(df['涨跌幅'].iloc[0]) if pd.notna(df['涨跌幅'].iloc[0]) else 0,
                    'open': float(df['今开'].iloc[0]) if pd.notna(df['今开'].iloc[0]) else 0,
                    'high': float(df['最高'].iloc[0]) if pd.notna(df['最高'].iloc[0]) else 0,
                    'low': float(df['最低'].iloc[0]) if pd.notna(df['最低'].iloc[0]) else 0,
                    'volume': float(df['成交量'].iloc[0]) if pd.notna(df['成交量'].iloc[0]) else 0,
                    'amount': float(df['成交额'].iloc[0]) if pd.notna(df['成交额'].iloc[0]) else 0,
                    'pre_close': float(df['昨收'].iloc[0]) if pd.notna(df['昨收'].iloc[0]) else 0,
                    'timestamp': datetime.now()
                }
        except Exception as e:
            logger.warning(f"获取失败: {e}")
            return {'status': 'failed', 'error': str(e)}

        return {'status': 'failed', 'error': '未知错误'}

    def get_realtime_quote_via_etf(self) -> Dict[str, Any]:
        try:
            df = ak.fund_etf_spot_sina()
            etf_row = df[df['symbol'] == 'sh' + self.ticker]
            if not etf_row.empty:
                return {
                    'status': 'success',
                    'data_source': 'fund_etf_spot_sina',
                    'price': float(etf_row['latest'].iloc[0]),
                    'open': float(etf_row['open'].iloc[0]) if pd.notna(etf_row['open'].iloc[0]) else 0,
                    'high': float(etf_row['high'].iloc[0]) if pd.notna(etf_row['high'].iloc[0]) else 0,
                    'low': float(etf_row['low'].iloc[0]) if pd.notna(etf_row['low'].iloc[0]) else 0,
                    'volume': float(etf_row['volume'].iloc[0]) if pd.notna(etf_row['volume'].iloc[0]) else 0,
                    'pre_close': float(etf_row['yestclose'].iloc[0]) if pd.notna(etf_row['yestclose'].iloc[0]) else 0,
                    'timestamp': datetime.now()
                }
        except Exception as e:
            logger.warning(f"ETF实时数据获取失败: {e}")
            return {'status': 'failed', 'error': str(e)}

        return {'status': 'failed', 'error': '未找到数据'}

    def get_historical_data(self, days: int = 30) -> Dict:
        try:
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')

            df = ak.stock_zh_a_hist(
                symbol=self.ticker,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust="qfq"
            )

            if not df.empty:
                return {
                    'status': 'success',
                    'data_source': 'akshare',
                    'data': df
                }
        except Exception as e:
            logger.warning(f"获取历史数据失败: {e}")
            return {'status': 'failed', 'error': str(e)}

        return {'status': 'failed', 'error': '未知错误'}


def test_mobile_data():
    print("=" * 60)
    print("移动端数据获取测试")
    print("=" * 60)

    fetcher = MobileDataFetcher()

    print("\n测试1: 获取实时行情（方法1: stock_zh_a_spot_em）...")
    result = fetcher.get_realtime_quote()

    if result['status'] == 'success':
        print("✅ 实时行情获取成功！")
        print(f"   数据源: {result.get('data_source', 'unknown')}")
        print(f"   最新价: {result['price']:.3f}")
        print(f"   涨跌额: {result['change']:+.3f}")
        print(f"   涨跌幅: {result['change_pct']:+.2f}%")
        print(f"   今开: {result['open']:.3f}")
        print(f"   最高: {result['high']:.3f}")
        print(f"   最低: {result['low']:.3f}")
        print(f"   成交量: {result['volume']:,.0f}")
        print(f"   成交额: {result['amount']:,.2f}")
        print(f"   更新时间: {result['timestamp']}")
    else:
        print(f"   ❌ 获取失败: {result.get('error', '未知错误')}")

    print("\n测试2: 获取实时行情（方法2: fund_etf_spot_sina）...")
    result = fetcher.get_realtime_quote_via_etf()

    if result['status'] == 'success':
        print("✅ 实时行情获取成功！")
        print(f"   数据源: {result.get('data_source', 'unknown')}")
        print(f"   最新价: {result['price']:.3f}")
        print(f"   今开: {result['open']:.3f}")
        print(f"   最高: {result['high']:.3f}")
        print(f"   最低: {result['low']:.3f}")
        print(f"   成交量: {result['volume']:,.0f}")
        print(f"   更新时间: {result['timestamp']}")
    else:
        print(f"   ❌ 获取失败: {result.get('error', '未知错误')}")

    print("\n测试3: 获取历史数据...")
    result = fetcher.get_historical_data(days=10)

    if result['status'] == 'success':
        print("✅ 历史数据获取成功！")
        print(f"   数据源: {result.get('data_source', 'unknown')}")
        print(f"   数据条数: {len(result['data'])}")
        print("\n最近5天数据:")
        print(result['data'].tail())
    else:
        print(f"   ❌ 获取失败: {result.get('error', '未知错误')}")

    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    test_mobile_data()
