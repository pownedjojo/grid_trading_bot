import plotly.graph_objects as go

class Plotter:
    def __init__(self, config_manager, grid_manager):
        self.config_manager = config_manager
        self.grid_manager = grid_manager

    def plot_results(self, data, grids, buy_orders, sell_orders):
        fig = self.create_base_figure(data)
        self.add_grid_lines(fig, grids)
        self.add_orders(fig, buy_orders, sell_orders)
        self.finalize_figure(fig)
        fig.show()

    def create_base_figure(self, data):
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=data.index, y=data['close'], mode='lines', name='Close Price', showlegend=False))
        return fig

    def add_grid_lines(self, fig, grids):
        central_price = self.grid_manager.get_central_price()
        for price in grids:
            if price < central_price:
                self.add_grid_line(fig, price, 'green')
            elif price > central_price:
                self.add_grid_line(fig, price, 'red')

    def add_grid_line(self, fig, price, color):
        fig.add_trace(go.Scatter(
            x=[fig.data[0].x[0], fig.data[0].x[-1]],
            y=[price, price],
            mode='lines',
            line=dict(color=color, dash='dash'),
            showlegend=False
        ))

    def add_orders(self, fig, buy_orders, sell_orders):
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

    def finalize_figure(self, fig):
        fig.update_layout(title='Grid Trading Strategy Results', xaxis_title='Time', yaxis_title='Price (USDT)', showlegend=False)