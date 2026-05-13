
import pandas as pd
import numpy as np
import akshare as ak
import yfinance as yf
from datetime import datetime, timedelta
import logging
from typing import Optional, Dict, Any
import time

from config import (
    TICKER, DATA_SOURCE, DATA_DIR, UPDATE_INTERVAL,
    TRADING_SESSION_MORNING_START, TRADING_SESSION_MORNING_END,
    TRADING_SESSION_AFTERNOON_START, TRADING_SESSION_AFTERNOON_END
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataFetcher:
    def __init__(self, ticker: str = TICKER, data_source: str = DATA_SOURCE):
        self.ticker = ticker
        self.data_source = data_source
        self.last_update = None
        self.cache = {}

    def fetch_historical_data(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: str = '1y'
    ) -> pd.DataFrame:
        try:
            if self.data_source == 'akshare':
                return self._fetch_akshare_historical(start_date, end_date, period)
            elif self.data_source == 'yfinance':
                return self._fetch_yfinance_historical(start_date, end_date, period)
            else:
                raise ValueError(f"不支持的数据源: {self.data_source}")
        except Exception as e:
            logger.error(f"获取历史数据失败: {e}")
            return self._generate_sample_data()

    def _fetch_akshare_historical(
        self,
        start_date: Optional[str],
        end_date: Optional[str],
        period: str
    ) -> pd.DataFrame:
        try:
            df = ak.fund_etf_hist_sina(symbol='sh518880')
            if '日期' in df.columns:
                df = df.rename(columns={
                    '日期': 'date',
                    '开盘': 'open',
                    '收盘': 'close',
                    '最高': 'high',
                    '最低': 'low',
                    '成交量': 'volume',
                })
                df['date'] = pd.to_datetime(df['date'])
                df = df.set_index('date').sort_index()

                if start_date:
                    df = df[df.index >= pd.to_datetime(start_date)]
                if end_date:
                    df = df[df.index <= pd.to_datetime(end_date)]

                return df
            else:
                logger.warning("数据格式不符合预期")
                return self._generate_sample_data()
        except Exception as e:
            logger.warning(f"AKShare获取失败，使用备选方案: {e}")
            return self._generate_sample_data()

    def _fetch_yfinance_historical(
        self,
        start_date: Optional[str],
        end_date: Optional[str],
        period: str
    ) -> pd.DataFrame:
        try:
            ticker_obj = yf.Ticker(self.ticker)
            df = ticker_obj.history(period=period, start=start_date, end=end_date)
            df = df.rename(columns={
                'Open': 'open',
                'Close': 'close',
                'High': 'high',
                'Low': 'low',
                'Volume': 'volume',
            })
            return df
        except Exception as e:
            logger.warning(f"yfinance获取失败，使用备选方案: {e}")
            return self._generate_sample_data()

    def get_realtime_quote(self) -> Dict[str, Any]:
        try:
            return self._get_akshare_realtime_em()
        except Exception as e:
            logger.error(f"获取实时行情失败: {e}")
            return self._get_mock_realtime()

    def _get_akshare_realtime_em(self) -> Dict[str, Any]:
        try:
            df = ak.stock_zh_a_spot_em(symbol="518880")
            if not df.empty:
                return {
                    'price': float(df['最新价'].iloc[0]),
                    'volume': int(df['成交量'].iloc[0]) if pd.notna(df['成交量'].iloc[0]) else 0,
                    'open': float(df['今开'].iloc[0]) if pd.notna(df['今开'].iloc[0]) else 0,
                    'high': float(df['最高'].iloc[0]) if pd.notna(df['最高'].iloc[0]) else 0,
                    'low': float(df['最低'].iloc[0]) if pd.notna(df['最低'].iloc[0]) else 0,
                    'pre_close': float(df['昨收'].iloc[0]) if pd.notna(df['昨收'].iloc[0]) else 0,
                    'change': float(df['涨跌额'].iloc[0]) if pd.notna(df['涨跌额'].iloc[0]) else 0,
                    'change_pct': float(df['涨跌幅'].iloc[0]) if pd.notna(df['涨跌幅'].iloc[0]) else 0,
                    'bid': float(df['买一'].iloc[0]) if pd.notna(df['买一'].iloc[0]) else 0,
                    'ask': float(df['卖一'].iloc[0]) if pd.notna(df['卖一'].iloc[0]) else 0,
                    'timestamp': datetime.now()
                }
            else:
                logger.warning("未找到518880数据，使用备选方案")
                return self._get_akshare_realtime_spot()
        except Exception as e:
            logger.warning(f"stock_zh_a_spot_em获取失败: {e}")
            return self._get_akshare_realtime_spot()

    def _get_akshare_realtime_spot(self) -> Dict[str, Any]:
        try:
            df = ak.fund_etf_spot_sina()
            etf_row = df[df['symbol'] == 'sh518880']
            if not etf_row.empty:
                return {
                    'price': float(etf_row['latest'].iloc[0]),
                    'volume': int(etf_row['volume'].iloc[0]) if pd.notna(etf_row['volume'].iloc[0]) else 0,
                    'open': float(etf_row['open'].iloc[0]) if pd.notna(etf_row['open'].iloc[0]) else 0,
                    'high': float(etf_row['high'].iloc[0]) if pd.notna(etf_row['high'].iloc[0]) else 0,
                    'low': float(etf_row['low'].iloc[0]) if pd.notna(etf_row['low'].iloc[0]) else 0,
                    'pre_close': float(etf_row['yestclose'].iloc[0]) if pd.notna(etf_row['yestclose'].iloc[0]) else 0,
                    'timestamp': datetime.now()
                }
            else:
                logger.warning("ETF实时数据未找到，使用模拟数据")
                return self._get_mock_realtime()
        except Exception as e:
            logger.warning(f"fund_etf_spot_sina获取失败: {e}")
            return self._get_mock_realtime()

    def fetch_intraday_data(
        self,
        date: Optional[str] = None,
        interval: str = '1m'
    ) -> pd.DataFrame:
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')

        try:
            if self.data_source == 'akshare':
                return self._fetch_akshare_intraday(date, interval)
            else:
                return self._generate_sample_intraday_data(date)
        except Exception as e:
            logger.error(f"获取日内数据失败: {e}")
            return self._generate_sample_intraday_data(date)

    def _fetch_akshare_intraday(self, date: str, interval: str) -> pd.DataFrame:
        try:
            df = ak.stock_zh_a_minute(
                symbol="518880",
                period="1",
                adjust=""
            )
            if not df.empty and '时间' in df.columns:
                df = df.rename(columns={
                    '时间': 'datetime',
                    '开盘': 'open',
                    '收盘': 'close',
                    '最高': 'high',
                    '最低': 'low',
                    '成交量': 'volume'
                })
                df['datetime'] = pd.to_datetime(df['datetime'])
                df = df.set_index('datetime').sort_index()
                return df
            else:
                logger.warning("分钟数据格式不符合预期")
                return self._generate_sample_intraday_data(date)
        except Exception as e:
            logger.warning(f"获取分钟级数据失败: {e}")
            return self._generate_sample_intraday_data(date)

    def _generate_sample_data(self) -> pd.DataFrame:
        dates = pd.date_range(start='2024-01-01', periods=250, freq='D')
        np.random.seed(42)

        base_price = 4.5
        returns = np.random.normal(0, 0.008, len(dates))
        prices = base_price * (1 + returns).cumprod()

        df = pd.DataFrame({
            'open': prices * (1 + np.random.normal(0, 0.002, len(dates))),
            'close': prices,
            'high': prices * (1 + np.abs(np.random.normal(0, 0.005, len(dates)))),
            'low': prices * (1 - np.abs(np.random.normal(0, 0.005, len(dates)))),
            'volume': np.random.randint(100000, 500000, len(dates))
        }, index=dates)

        return df

    def _generate_sample_intraday_data(self, date: str) -> pd.DataFrame:
        date_obj = pd.to_datetime(date)

        times = []
        for hour in [9, 10, 11]:
            for minute in range(0, 60):
                if hour == 9 and minute < 30:
                    continue
                if hour == 11 and minute >= 30:
                    continue
                times.append(f"{hour:02d}:{minute:02d}")
        for hour in [13, 14]:
            for minute in range(0, 60):
                times.append(f"{hour:02d}:{minute:02d}")
        times.append("15:00")

        num_points = len(times)
        np.random.seed(int(date_obj.timestamp()) % 10000)

        base_price = 4.5 + np.random.normal(0, 0.1)
        trend = np.linspace(0, np.random.normal(0, 0.01), num_points)
        noise = np.random.normal(0, 0.003, num_points)
        prices = base_price * (1 + trend + noise)

        df = pd.DataFrame({
            'time': times,
            'price': prices,
            'volume': np.random.randint(1000, 50000, num_points)
        })

        df['datetime'] = pd.to_datetime(f"{date} " + df['time'])
        df = df.set_index('datetime')
        return df

    def _get_mock_realtime(self) -> Dict[str, Any]:
        now = datetime.now()
        base_price = 4.5
        time_factor = np.sin(now.hour * 60 + now.minute) * 0.005
        random_factor = np.random.normal(0, 0.001)
        price = base_price * (1 + time_factor + random_factor)

        return {
            'price': round(price, 3),
            'volume': np.random.randint(10000, 50000),
            'open': round(base_price * 0.999, 3),
            'high': round(base_price * 1.005, 3),
            'low': round(base_price * 0.995, 3),
            'pre_close': round(base_price, 3),
            'timestamp': now
        }

    def is_trading_time(self, dt: Optional[datetime] = None) -> bool:
        if dt is None:
            dt = datetime.now()

        weekday = dt.strftime('%a')
        if weekday not in ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']:
            return False

        time_str = dt.strftime('%H:%M:%S')
        morning_session = TRADING_SESSION_MORNING_START <= time_str <= TRADING_SESSION_MORNING_END
        afternoon_session = TRADING_SESSION_AFTERNOON_START <= time_str <= TRADING_SESSION_AFTERNOON_END

        return morning_session or afternoon_session

    def save_data(self, df: pd.DataFrame, filename: str):
        filepath = f"{DATA_DIR}/{filename}.csv"
        df.to_csv(filepath)
        logger.info(f"数据已保存到 {filepath}")

    def load_data(self, filename: str) -> pd.DataFrame:
        filepath = f"{DATA_DIR}/{filename}.csv"
        try:
            return pd.read_csv(filepath, index_col=0, parse_dates=True)
        except Exception as e:
            logger.error(f"加载数据失败: {e}")
            return pd.DataFrame()
