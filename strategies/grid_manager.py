import numpy as np

class GridManager:
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.bottom_range, self.top_range, self.num_grids, self.spacing_type, self.percentage_spacing = self._extract_config()
        self.grids = self._calculate_grids()
        self.central_price = self._calculate_central_price()
    
    def get_central_price(self):
        return self.central_price

    def _extract_config(self):
        bottom_range = self.config_manager.get_bottom_range()
        top_range = self.config_manager.get_top_range()
        num_grids = self.config_manager.get_num_grids()
        spacing_type = self.config_manager.get_spacing_type()
        percentage_spacing =  self.config_manager.get_percentage_spacing()
        return bottom_range, top_range, num_grids, spacing_type, percentage_spacing

    def _calculate_grids(self):
        if self.spacing_type == 'arithmetic':
            return np.linspace(self.bottom_range, self.top_range, self.num_grids)
        elif self.spacing_type == 'geometric':
            grids = [self.bottom_range]
            for _ in range(1, self.num_grids):
                grids.append(grids[-1] * (1 + self.percentage_spacing))
            return np.array(grids)
        else:
            raise ValueError("Invalid spacing_type - spacing_type must be either 'arithmetic' or 'geometric'")
    
    def _calculate_central_price(self):
        if self.spacing_type == 'arithmetic':
            return (self.top_range + self.bottom_range) / 2
        elif self.spacing_type == 'geometric':
            return (self.top_range * self.bottom_range) ** self.percentage_spacing
        else:
            raise ValueError("Invalid spacing_type - spacing_type must be either 'arithmetic' or 'geometric'")