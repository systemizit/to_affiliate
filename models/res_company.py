from odoo import models, fields, api


class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.model
    def _default_commission_product(self):
        return self.env.ref('to_affiliate.to_product_product_aff_commission', raise_if_not_found=False)
    
    affiliate_comm_percentage = fields.Float('Affiliate Commission Percentage', default=10.0)
    affiliate_cookie_age = fields.Integer('Affiliate Cookie Lifetime', default=864000, help='The lifetime of a cookie in seconds')
    affiliate_min_payout = fields.Float('Minimum Commission Payout', default=100.0)
    commission_product_id = fields.Many2one('product.product', 'Default Commission Product', domain=[('type', '=', 'service')],
                                            default=_default_commission_product,
                                            help="The standard Odoo product for accounting integration purpose")
    aff_allowed = fields.Boolean('Affiliate Allowed', help="Enable this option will allow clients to select this company when joining affiliate program",
                                 default=True)
    compute_aff_method = fields.Selection([
        ('after_discount', 'After Discount'),
        ('before_discount', 'Before Discount'),
        ], string='Affiliate Commission Computation', default='after_discount', required=True,
        help="Selecting affiliate commission computation method by either Before Discount or After Discount")
