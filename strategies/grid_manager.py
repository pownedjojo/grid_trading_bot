import numpy as np

class GridManager:
    def __init__(self, low_price, high_price, num_grids, spacing_type, percentage_spacing):
        self.low_price = low_price
        self.high_price = high_price
        self.num_grids = num_grids
        self.spacing_type = spacing_type
        self.percentage_spacing = percentage_spacing
        self.grids = self.calculate_grids()

    def calculate_grids(self):
        if self.spacing_type == 'arithmetic':
            return np.linspace(self.low_price, self.high_price, self.num_grids)
        elif self.spacing_type == 'geometric':
            grids = [self.low_price]
            for _ in range(1, self.num_grids):
                grids.append(grids[-1] * (1 + self.percentage_spacing))
            return np.array(grids)
        else:
            raise ValueError("spacing_type must be either 'arithmetic' or 'geometric'")