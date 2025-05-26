import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from sqlalchemy import create_engine
from pathlib import Path
import logging
import logging.config
from src.config import LOG_CONFIG

# Configure logging
logging.config.dictConfig(LOG_CONFIG)
logger = logging.getLogger(__name__)

def load_etf_data(symbol: str, db_path: str) -> pd.DataFrame:
    """Load ETF data from SQLite database."""
    engine = create_engine(f"sqlite:///{db_path}")
    query = f"SELECT * FROM daily_prices WHERE symbol = '{symbol}' ORDER BY date"
    return pd.read_sql(query, engine)

def create_ohlcv_chart(df: pd.DataFrame, symbol: str) -> go.Figure:
    """Create an interactive OHLCV chart using Plotly."""
    # Create figure with secondary y-axis
    fig = make_subplots(rows=2, cols=1, 
                       shared_xaxes=True,
                       vertical_spacing=0.03,
                       row_heights=[0.7, 0.3])

    # Add candlestick chart
    fig.add_trace(
        go.Candlestick(
            x=df['date'],
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name='OHLC'
        ),
        row=1, col=1
    )

    # Add volume bar chart
    colors = ['red' if row['close'] < row['open'] else 'green' 
              for _, row in df.iterrows()]
    
    fig.add_trace(
        go.Bar(
            x=df['date'],
            y=df['volume'],
            name='Volume',
            marker_color=colors
        ),
        row=2, col=1
    )

    # Update layout
    fig.update_layout(
        title=f'{symbol} Daily OHLCV Chart',
        yaxis_title='Price',
        yaxis2_title='Volume',
        xaxis_rangeslider_visible=False,
        template='plotly_white',
        height=800,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )

    # Update y-axes labels
    fig.update_yaxes(title_text="Price", row=1, col=1)
    fig.update_yaxes(title_text="Volume", row=2, col=1)

    return fig

def main():
    # Database path
    db_path = Path('data/tushare/market_data.db')
    if not db_path.exists():
        logger.error(f"Database file not found: {db_path}")
        return

    # Load data
    symbol = '159696'
    try:
        df = load_etf_data(symbol, db_path)
        if df.empty:
            logger.error(f"No data found for {symbol}")
            return

        # Create chart
        fig = create_ohlcv_chart(df, symbol)

        # Save as HTML
        output_path = Path('data/tushare/etf_chart.html')
        fig.write_html(str(output_path))
        logger.info(f"Chart saved to {output_path}")

    except Exception as e:
        logger.error(f"Error creating chart: {str(e)}")

if __name__ == '__main__':
    main() 