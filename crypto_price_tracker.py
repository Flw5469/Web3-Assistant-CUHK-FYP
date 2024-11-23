import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import time

# Set page title and favicon
st.set_page_config(
    page_title="Crypto Price Tracker",
    page_icon="📈"
)

def get_coin_list():
    """Get list of top trading pairs from Binance"""
    try:
        # Priority coins that should always be included if available
        priority_coins = ['BTC', 'ETH', 'BNB', 'XRP', 'SOL', 'ADA', 'DOGE']
        
        # Common cryptocurrency name mappings
        coin_names = {
            'BTC': 'Bitcoin',
            'ETH': 'Ethereum',
            'BNB': 'Binance Coin',
            'XRP': 'Ripple',
            'SOL': 'Solana',
            'ADA': 'Cardano',
            'DOGE': 'Dogecoin',
            'MATIC': 'Polygon',
            'DOT': 'Polkadot',
            'AVAX': 'Avalanche'
        }

        url = 'https://api.binance.com/api/v3/ticker/24hr'
        response = requests.get(url)
        
        if response.status_code != 200:
            st.error(f"API returned status code: {response.status_code}")
            return {}
            
        data = response.json()
        
        # First, get priority coins
        formatted_pairs = {}
        for coin in priority_coins:
            symbol = f"{coin}USDT"
            pair = next((item for item in data if item['symbol'] == symbol), None)
            if pair:
                formatted_pairs[symbol] = f"{coin_names.get(coin, coin)} (USDT)"
        
        # Then add remaining top volume pairs until we have 10 total
        usdt_pairs = [
            item for item in data 
            if item['symbol'].endswith('USDT') 
            and item['symbol'] not in formatted_pairs
        ]
        sorted_pairs = sorted(usdt_pairs, key=lambda x: float(x['volume']), reverse=True)
        
        for item in sorted_pairs:
            if len(formatted_pairs) >= 10:
                break
            symbol = item['symbol'].replace('USDT', '')
            formatted_pairs[item['symbol']] = f"{coin_names.get(symbol, symbol)} (USDT)"
        
        return formatted_pairs
        
    except Exception as e:
        st.error(f"Error fetching coin list: {str(e)}")
        return {}

def get_hkd_rate():
    """Get current HKD/USDT exchange rate"""
    try:
        url = 'https://api.binance.com/api/v3/ticker/price'
        params = {'symbol': 'USDTHKD'}  # or use a forex API if this pair isn't available
        response = requests.get(url, params=params)
        if response.status_code == 200:
            return float(response.json()['price'])
        else:
            # Fallback to approximate HKD rate if API fails
            return 7.85  # Approximate HKD/USD rate
    except Exception:
        return 7.85  # Fallback rate

def get_current_price(symbol):
    """Get current price for a specific coin in HKD"""
    try:
        url = f'https://api.binance.com/api/v3/ticker/price'
        params = {'symbol': symbol}
        response = requests.get(url, params=params)
        data = response.json()
        usdt_price = float(data['price'])
        hkd_rate = get_hkd_rate()
        return usdt_price * hkd_rate
    except Exception as e:
        st.error(f"Error fetching current price: {e}")
        return None

def get_coin_price_history(symbol):
    """Get historical price data for a specific coin in HKD"""
    try:
        url = 'https://api.binance.com/api/v3/klines'
        params = {
            'symbol': symbol,
            'interval': '1s',
            'limit': 600
        }
        
        response = requests.get(url, params=params)
        
        if response.status_code != 200:
            st.error(f"API returned status code: {response.status_code}")
            return None
            
        data = response.json()
        
        # Convert to DataFrame
        df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 
                                       'quote_volume', 'trades', 'taker_buy_base', 'taker_buy_quote', 'ignore'])
        
        # Convert timestamp to datetime and keep only timestamp and close price
        df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
        df['price'] = df['close'].astype(float) * get_hkd_rate()  # Convert to HKD
        
        return df[['date', 'price']]
        
    except Exception as e:
        st.error(f"Error fetching price history: {str(e)}")
        return None

def main():
    st.title("Cryptocurrency Price Tracker 📈")
    
    # Get list of available coins
    coins = get_coin_list()
    
    if not coins:
        st.error("No trading pairs available")
        return
    
    # Create dropdown for coin selection
    selected_coin = st.selectbox(
        "Select a cryptocurrency:",
        options=list(coins.keys()),
        format_func=lambda x: coins[x]
    )
    
    if selected_coin:
        # Create placeholder for price updates
        price_placeholder = st.empty()
        chart_placeholder = st.empty()
        
        while True:
            # Get current price
            current_price = get_current_price(selected_coin)
            print(selected_coin)
            if current_price:
                # Update price display
                with price_placeholder:
                    st.metric(
                        label=f"Current {coins[selected_coin]} Price",
                        value=f"HK${current_price:,.2f}"
                    )
            
            # Get historical price data
            df = get_coin_price_history(selected_coin)
            if df is not None:
                # Create price chart using matplotlib
                fig, ax = plt.subplots(figsize=(10, 6))
                ax.plot(df['date'], df['price'])
                
                # Customize the plot
                ax.set_title(f'{coins[selected_coin]} Price History (Last 10 Minutes)')
                ax.set_xlabel('Date')
                ax.set_ylabel('Price (HKD)')
                
                # Rotate x-axis labels
                plt.xticks(rotation=45)
                
                # Add grid
                ax.grid(True, linestyle='--', alpha=0.7)
                
                # Format y-axis
                ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{int(x):,}' if x >= 1 else f'{x:.4f}'))
                
                # Adjust layout
                plt.tight_layout()
                
                # Update chart display
                with chart_placeholder:
                    st.pyplot(fig)
                plt.close(fig)  # Clear figure to free memory
            
            # Add last updated time
            # st.text(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Wait 5 seconds before next update
            time.sleep(1)

if __name__ == "__main__":
    main() 