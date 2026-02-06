# forex_analyzer.py
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import logging
import time
import matplotlib.pyplot as plt
import os


# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ForexAnalyzer:
    def __init__(self):
        self.supported_pairs = {
            'GBPUSD': 'GBPUSD=X',
            'EURUSD': 'EURUSD=X', 
            'USDJPY': 'USDJPY=X',
            'AUDUSD': 'AUDUSD=X',
            'USDCAD': 'USDCAD=X',
            'USDCHF': 'USDCHF=X',
            'NZDUSD': 'NZDUSD=X',
            'EURGBP': 'EURGBP=X'
        }
        
    def get_symbol(self, pair_name):
        """Получаем символ для Yahoo Finance"""
        pair_name = pair_name.upper().replace('/', '')
        return self.supported_pairs.get(pair_name, f"{pair_name}=X")
    
    def analyze_pair(self, pair_name):
        """Анализ конкретной валютной пары"""
        try:
            symbol = self.get_symbol(pair_name)
            logger.info(f"🔍 Анализируем {pair_name} ({symbol})...")
            
            # ЗАГРУЖАЕМ ДНЕВНЫЕ ДАННЫЕ ДЛЯ ATR!
            daily_data = yf.download(
                tickers=symbol, 
                period='3mo',  # 3 месяца дневных данных
                interval='1d',  # ДНЕВНОЙ таймфрейм!
                progress=False,
                auto_adjust=True
            )
            
            # И отдельно текущие данные для цены
            current_data = yf.download(
                tickers=symbol,
                period='1d',
                interval='1h',
                progress=False,
                auto_adjust=True
            )
            
            if daily_data is None or daily_data.empty or current_data is None or current_data.empty:
                logger.warning(f"❌ Данные пустые для {pair_name}")
                return self.create_demo_data(pair_name)
                
            # Нормализуем колонки
            daily_data = self.normalize_columns(daily_data, symbol)
            current_data = self.normalize_columns(current_data, symbol)
            
            logger.info(f"✅ Дневные данные: {len(daily_data)} записей")
            logger.info(f"✅ Текущие данные: {len(current_data)} записей")

            chart_path = self.generate_price_chart(daily_data, pair_name)
            if chart_path:
                logger.info(f"✅ График сохранен: {chart_path}")
            else:
                logger.warning(f"❌ Не удалось создать график для {pair_name}")
                


            
            # Проверяем наличие необходимых колонок
            required_cols = ['OPEN', 'HIGH', 'LOW', 'CLOSE']
            missing_cols_daily = [col for col in required_cols if col not in daily_data.columns]
            missing_cols_current = [col for col in required_cols if col not in current_data.columns]
            
            if missing_cols_daily or missing_cols_current:
                logger.error(f"❌ Отсутствуют колонки в daily: {missing_cols_daily}, в current: {missing_cols_current}")
                return self.create_demo_data(pair_name)
            
            # Расчет показателей
            results = self.calculate_metrics(daily_data, current_data, pair_name)
            return results
            
        except Exception as e:
            logger.error(f"❌ Критическая ошибка анализа {pair_name}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return self.create_demo_data(pair_name)
    
    def calculate_metrics(self, daily_data, current_data, pair_name):
        """Расчет всех метрик на основе дневных данных"""
        try:
            # Текущая цена из последних данных
            current_price = self._get_float_value(current_data['CLOSE'].iloc[-1])
            logger.info(f"💰 Текущая цена: {current_price}")
            
            # Дневной ATR из ДНЕВНЫХ данных
            daily_atr = self.calculate_daily_atr(daily_data)
            logger.info(f"📊 Дневной ATR: {daily_atr} пипсов")
            
            # Тренд на основе дневных данных
            trend = self.calculate_trend(daily_data)
            logger.info(f"🎯 Тренд: {trend}")
            
            # Волатильность
            volatility = self.calculate_volatility_level(daily_atr)
            
            # Рекомендация
            recommendation = self.generate_recommendation(trend, volatility, daily_atr)
            
            # Дополнительная статистика
            stats = self.calculate_additional_stats(daily_data)
            
            return {
                'pair': pair_name,
                'current_price': current_price,
                'daily_atr': daily_atr,
                'trend': trend,
                'volatility': volatility,
                'recommendation': recommendation,
                'timestamp': datetime.now().strftime('%H:%M %d.%m.%Y'),
                'is_demo': False,
                'stats': stats
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка расчета метрик: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return self.create_demo_data(pair_name)
    
    def calculate_daily_atr(self, daily_data, period=14):
        """Расчет ATR на основе ДНЕВНЫХ данных"""
        try:
            if len(daily_data) < period:
                logger.warning(f"Недостаточно дневных данных для ATR: {len(daily_data)}")
                return 85.0  # Среднее значение для GBPUSD
            
            high = daily_data['HIGH']
            low = daily_data['LOW'] 
            close = daily_data['CLOSE']
            
            # Классический расчет ATR
            high_low = high - low
            high_close = np.abs(high - close.shift())
            low_close = np.abs(low - close.shift())
            
            true_range = np.maximum(high_low, np.maximum(high_close, low_close))
            atr = true_range.rolling(window=period).mean()
            
            # Безопасное получение значения
            if not atr.empty:
                atr_value = self._get_float_value(atr.iloc[-1])
                result = round(atr_value * 10000, 1)  # Конвертируем в пипсы
                
                # Проверяем реалистичность значения
                if result < 20 or result > 300:
                    logger.warning(f"ATR выглядит нереалистично: {result}, используем среднее")
                    return 85.0
                    
            else:
                result = 85.0
                
            logger.info(f"Дневной ATR рассчитан: {result} пипсов")
            return result
            
        except Exception as e:
            logger.error(f"❌ Ошибка расчета дневного ATR: {e}")
            return 85.0
    
    def calculate_trend(self, daily_data):
        """Определение тренда на основе дневных данных"""
        try:
            if len(daily_data) < 20:
                return "❓ Недостаточно данных"
                
            close_prices = daily_data['CLOSE']
            
            # EMA для тренда
            ema_20 = close_prices.ewm(span=20).mean()
            ema_50 = close_prices.ewm(span=50).mean()
            
            current_price = self._get_float_value(close_prices.iloc[-1])
            current_ema20 = self._get_float_value(ema_20.iloc[-1])
            current_ema50 = self._get_float_value(ema_50.iloc[-1])
            
            # Процентные отклонения
            price_vs_ema20 = (current_price - current_ema20) / current_ema20 * 100
            ema20_vs_ema50 = (current_ema20 - current_ema50) / current_ema50 * 100
            
            if price_vs_ema20 > 0.5 and ema20_vs_ema50 > 0.2:
                return "📈 Сильный восходящий"
            elif price_vs_ema20 > 0.1:
                return "↗️ Восходящий" 
            elif price_vs_ema20 < -0.5 and ema20_vs_ema50 < -0.2:
                return "📉 Сильный нисходящий"
            elif price_vs_ema20 < -0.1:
                return "↘️ Нисходящий"
            else:
                return "➡️ Боковой"
                
        except Exception as e:
            logger.error(f"❌ Ошибка определения тренда: {e}")
            return "❓ Неопределенный"
    
    def calculate_additional_stats(self, daily_data):
        """Дополнительная статистика"""
        try:
            if len(daily_data) < 5:
                return {}
                
            # Средний дневной диапазон за последние 30 дней
            recent_data = daily_data.tail(30)
            daily_ranges = (recent_data['HIGH'] - recent_data['LOW']) * 10000
            avg_daily_range = round(daily_ranges.mean(), 1)
            max_daily_range = round(daily_ranges.max(), 1)
            
            # Волатильность (стандартное отклонение)
            daily_returns = recent_data['CLOSE'].pct_change().dropna()
            volatility_pct = round(daily_returns.std() * 100, 2)
            
            return {
                'avg_daily_range': avg_daily_range,
                'max_daily_range': max_daily_range,
                'volatility_percent': volatility_pct
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка расчета дополнительной статистики: {e}")
            return {}
    
    def normalize_columns(self, data, symbol):
        """Нормализует названия колонок из формата кортежей"""
        try:
            new_columns = []
            for col in data.columns:
                if isinstance(col, tuple):
                    new_col = col[0].upper()
                    new_columns.append(new_col)
                else:
                    new_columns.append(str(col).upper())
            
            data.columns = new_columns
            return data
            
        except Exception as e:
            logger.error(f"❌ Ошибка нормализации колонок: {e}")
            return data
    
    def _get_float_value(self, value):
        """Безопасное получение float значения"""
        try:
            if hasattr(value, 'iloc'):
                if len(value) == 1:
                    return float(value.iloc[0])
                else:
                    return float(value.values[0]) if len(value) > 0 else 0.0
            elif hasattr(value, 'item'):
                return float(value.item())
            else:
                return float(value)
        except Exception as e:
            logger.warning(f"Ошибка преобразования в float: {e}, значение: {value}")
            return 0.0
    
    def calculate_volatility_level(self, atr):
        """Уровень волатильности на основе реальных значений GBPUSD"""
        if atr > 100:
            return "🔴 Высокая"
        elif atr > 70:
            return "🟡 Средняя"
        else:
            return "🟢 Низкая"
    
    def generate_recommendation(self, trend, volatility, atr):
        """Генерация торговой рекомендации"""
        try:
            recommendations = []
            
            if "восходящий" in trend.lower():
                recommendations.append("Рассмотрите покупки")
            elif "нисходящий" in trend.lower():
                recommendations.append("Рассмотрите продажи")
            else:
                recommendations.append("Торгуйте в рамках диапазона")
            
            if "высокая" in volatility.lower():
                recommendations.append("Используйте широкие стоп-лоссы")
                recommendations.append("Хорошо для свинг-трейдинга")
            elif "низкая" in volatility.lower():
                recommendations.append("Подходит для скальпинга")
                recommendations.append("Используйте узкие стоп-лоссы")
            
            # Более реалистичные стоп-лоссы
            if atr > 100:
                stop_loss = round(atr * 0.4)
            elif atr > 70:
                stop_loss = round(atr * 0.3)
            else:
                stop_loss = round(atr * 0.25)
                
            stop_loss = max(20, stop_loss)  # Минимум 20 пипсов
            recommendations.append(f"Рекомендуемый стоп-лосс: {stop_loss} пипсов")
            
            return ". ".join(recommendations)
            
        except Exception as e:
            logger.error(f"❌ Ошибка генерации рекомендаций: {e}")
            return "Используйте стандартные параметры риска"
    
    def create_demo_data(self, pair_name):
        """Создание демо-данных с реалистичными значениями"""
        logger.info(f"🔄 Создаем демо-данные для {pair_name}")
        
        base_prices = {
            'GBPUSD': 1.2650, 'EURUSD': 1.0950, 'USDJPY': 147.80,
            'AUDUSD': 0.6650, 'USDCAD': 1.3400, 'USDCHF': 0.8700,
            'NZDUSD': 0.6200, 'EURGBP': 0.8650
        }
        
        base_price = base_prices.get(pair_name, 1.0000)
        
        import random
        current_price = base_price + random.uniform(-0.005, 0.005)
        daily_atr = random.uniform(70, 110)  # Реалистичный ATR для Forex
        
        return {
            'pair': pair_name,
            'current_price': round(current_price, 5),
            'daily_atr': round(daily_atr, 1),
            'trend': random.choice(["📈 Восходящий", "📉 Нисходящий", "➡️ Боковой"]),
            'volatility': random.choice(["🟢 Низкая", "🟡 Средняя", "🔴 Высокая"]),
            'recommendation': "Это демо-данные. Реальные данные временно недоступны.",
            'timestamp': datetime.now().strftime('%H:%M %d.%m.%Y'),
            'is_demo': True
        }
    
    def get_supported_pairs(self):
        """Список поддерживаемых пар"""
        return list(self.supported_pairs.keys())
    
#=================================================================

def generate_price_chart(self, daily_data, pair_name):
    """
    Генерирует PNG-график цены
    """
    try:
        plt.figure(figsize=(10, 5))
        
        plt.plot(daily_data.index, daily_data['CLOSE'], label='Close', linewidth=2)
        
        # EMA
        ema20 = daily_data['CLOSE'].ewm(span=20).mean()
        ema50 = daily_data['CLOSE'].ewm(span=50).mean()
        
        plt.plot(daily_data.index, ema20, label='EMA 20', linestyle='--')
        plt.plot(daily_data.index, ema50, label='EMA 50', linestyle='--')
        
        plt.title(f"{pair_name} — Daily Chart")
        plt.xlabel("Date")
        plt.ylabel("Price")
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        filename = f"{pair_name}_chart.png"
        plt.tight_layout()
        plt.savefig(filename, dpi=150)
        plt.close()
        
        return filename
        
    except Exception as e:
        logger.error(f"Ошибка генерации графика: {e}")
        return None

