from odoo import fields, models


class AffiliateConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    affiliate_comm_percentage = fields.Float(string="Default Commission Percentage", related='company_id.affiliate_comm_percentage', readonly=False)
    cookie_age = fields.Integer(string="Cookie Life", related='company_id.affiliate_cookie_age', readonly=False)
    affiliate_min_payout = fields.Float(string="Minimum Payout", related='company_id.affiliate_min_payout', readonly=False)
    commission_product_id = fields.Many2one('product.product', string="Default Commission Product",
        related='company_id.commission_product_id', domain=[('type', '=', 'service')], readonly=False)
    compute_aff_method = fields.Selection(related='company_id.compute_aff_method', readonly=False)
