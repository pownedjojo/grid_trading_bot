from typing import List
import plotly.graph_objects as go
import pandas as pd
from core.grid_management.grid_manager import GridManager
from core.order_handling.order import Order
from core.order_handling.order_book import OrderBook

class Plotter:
    def __init__(self, grid_manager: GridManager, order_book: OrderBook):
        self.grid_manager = grid_manager
        self.order_book = order_book

    def plot_results(self, data: pd.DataFrame) -> None:
        fig = self.create_base_figure(data)
        grids, central_price = self.grid_manager.price_grids, self.grid_manager.central_price
        self.add_grid_lines(fig, grids, central_price)
        buy_orders = self.order_book.get_all_buy_orders()
        sell_orders = self.order_book.get_all_sell_orders()
        self.add_orders(fig, buy_orders, sell_orders)
        self.finalize_figure(fig)
        fig.show()

    def create_base_figure(self, data: pd.DataFrame) -> go.Figure:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=data.index, y=data['close'], mode='lines', name='Close Price', showlegend=False))
        return fig

    def add_grid_lines(self, fig: go.Figure, grids: List[float], central_price: float) -> None:
        for price in grids:
            if price < central_price:
                self.add_grid_line(fig, price, 'green')
            elif price > central_price:
                self.add_grid_line(fig, price, 'red')

    def add_grid_line(self, fig: go.Figure, price: float, color: str) -> None:
        fig.add_trace(go.Scatter(
            x=[fig.data[0].x[0], fig.data[0].x[-1]],
            y=[price, price],
            mode='lines',
            line=dict(color=color, dash='dash'),
            showlegend=False
        ))

    def add_orders(self, fig: go.Figure, buy_orders: List[Order], sell_orders: List[Order]) -> None:
        for order in buy_orders:
            fig.add_trace(go.Scatter(
                x=[order.timestamp],
                y=[order.price],
                mode='markers',
                marker=dict(symbol='triangle-up', color='green', size=10),
                name='Buy Order',
                text=f"Buy\nPrice: {order.price}\nQty: {order.quantity}\nDate: {order.timestamp}",
                hoverinfo='text'
            ))

        for order in sell_orders:
            fig.add_trace(go.Scatter(
                x=[order.timestamp],
                y=[order.price],
                mode='markers',
                marker=dict(symbol='triangle-down', color='red', size=10),
                name='Sell Order',
                text=f"Sell\nPrice: {order.price}\nQty: {order.quantity}\nDate: {order.timestamp}",
                hoverinfo='text'
            ))

    def finalize_figure(self, fig: go.Figure) -> None:
        fig.update_layout(title='Grid Trading Strategy Results', xaxis_title='Time', yaxis_title='Price (USDT)', showlegend=False)