from plotly.subplots import make_subplots
from typing import List
import plotly.graph_objects as go
import pandas as pd
from core.grid_management.grid_manager import GridManager
from core.order_handling.order import Order, OrderSide
from core.order_handling.order_book import OrderBook

class Plotter:
    def __init__(self, grid_manager: GridManager, order_book: OrderBook):
        self.grid_manager = grid_manager
        self.order_book = order_book

    def plot_results(self, data: pd.DataFrame) -> None:
        fig = make_subplots(
            rows=3,
            cols=1,
            shared_xaxes=True,
            row_heights=[0.70, 0.15, 0.15],
            vertical_spacing=0.03
        )

        self._add_candlestick_trace(fig, data)
        self._add_grid_lines(fig, self.grid_manager.price_grids, self.grid_manager.central_price)
        self._add_trade_markers(fig, self.order_book.get_completed_orders())
        self._add_volume_trace(fig, data)

        self._add_account_value_trace(fig, data)

        fig.update_layout(
            title="Grid Trading Strategy Results",
            yaxis_title="Price (USDT)",
            yaxis2_title="Volume",
            yaxis3_title="P/L",
            xaxis=dict(rangeslider=dict(visible=False)),
            showlegend=False,
        )
        fig.show()

    def _add_candlestick_trace(self, fig: go.Figure, data: pd.DataFrame) -> None:
        fig.add_trace(
            go.Candlestick(
                x=data.index,
                open=data['open'],
                high=data['high'],
                low=data['low'],
                close=data['close'],
                name="Candlesticks",
            ),
            row=1, col=1
        )
    
    def _add_grid_lines(
        self, 
        fig: go.Figure, 
        grids: List[float], 
        central_price: float
    ) -> None:
        for price in grids:
            color = 'green' if price < central_price else 'red'
            fig.add_trace(go.Scatter(
                x=[fig.data[0].x[0], fig.data[0].x[-1]],
                y=[price, price],
                mode='lines',
                line=dict(color=color, dash='dash'),
                showlegend=False
            ))

    def _add_trade_markers(self, fig: go.Figure, orders: List[Order]) -> None:
        for order in orders:
            icon_name = 'triangle-up' if order.side == OrderSide.BUY else 'triangle-down'
            icon_color = 'green' if order.side == OrderSide.BUY else 'red'
            fig.add_trace(
                go.Scatter(
                    x=[order.format_last_trade_timestamp()],
                    y=[order.price],
                    mode='markers',
                    marker=dict(symbol=icon_name, color=icon_color, size=10),
                    name=f'{order.side.name} Order',
                    text=f"Price: {order.price}\nQty: {order.filled}\nDate: {order.format_last_trade_timestamp()}",
                    hoverinfo='x+y+text',
                ),
                row=1, col=1
            )

    def _add_volume_trace(self, fig: go.Figure, data: pd.DataFrame) -> None:
        volume_colors = ['green' if close >= open_ else 'red' for close, open_ in zip(data['close'], data['open'])]
        
        fig.add_trace(
            go.Bar(
                x=data.index,
                y=data['volume'],
                name="Volume",
                marker=dict(color=volume_colors),
                opacity=0.7,
            ),
            row=2, col=1
        )
        
        fig.update_yaxes(
            title="Volume",
            row=2, col=1,
            gridcolor="lightgray",
        )
    
    def _add_account_value_trace(self, fig: go.Figure, data: pd.DataFrame) -> None:
        fig.add_trace(
            go.Scatter(
                x=data.index,
                y=data['account_value'],
                mode='lines',
                name="Account Value",
                line=dict(color='purple', width=2),
            ),
            row=3, col=1
        )