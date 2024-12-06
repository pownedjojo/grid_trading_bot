from typing import List
import plotly.graph_objects as go
import pandas as pd
from core.grid_management.grid_manager import GridManager
from core.order_handling.order import Order, OrderSide
from core.order_handling.order_book import OrderBook

class Plotter:
    def __init__(
        self, 
        grid_manager: GridManager,
        order_book: OrderBook
    ):
        self.grid_manager = grid_manager
        self.order_book = order_book

    def plot_results(
        self,
        data: pd.DataFrame
    ) -> None:
        fig = self._create_base_figure(data)
        grids, central_price = self.grid_manager.price_grids, self.grid_manager.central_price
        # self._add_volume_trace(fig, data)
        self._add_grid_lines(fig, grids, central_price)
        self._add_trade_markers(fig, self.order_book.get_completed_orders())
        fig.update_layout(
            title="Grid Trading Strategy Results",
            xaxis_title="Time",
            yaxis_title="Price (USDT)",
            yaxis2=dict(title="Volume", overlaying="y", side="right", showgrid=False),
            showlegend=False,
        )
        fig.show()

    def _create_base_figure(
        self, 
        data: pd.DataFrame
    ) -> go.Figure:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=data.index, y=data['close'], mode='lines', name='Close Price', showlegend=False))
        return fig

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

    def _add_trade_markers(
        self, 
        fig: go.Figure, 
        orders: List[Order]
    ) -> None:
        for order in orders:
            icon_name = 'triangle-up' if order.side == OrderSide.BUY else 'triangle-down'
            icon_color = 'green' if order.side == OrderSide.BUY else 'red'
            fig.add_trace(go.Scatter(
                x=[order.format_last_trade_timestamp()],
                y=[order.price],
                mode='markers',
                marker=dict(symbol=icon_name, color=icon_color, size=10),
                name=f'{order.side.name} Order',
                text=f"Price: {order.price}\nQty: {order.filled}\nDate: {order.format_last_trade_timestamp()}",
                hoverinfo='text'
            ))