from odoo import models


class Product(models.Model):
    _inherit = 'product.product'

    def _is_child_of(self, category_ids):
        self.ensure_one()
        if category_ids:
            product = self.env['product.product'].search([('categ_id', 'child_of', category_ids), ('id', '=', self.id)])
            if product:
                return True
        return False
