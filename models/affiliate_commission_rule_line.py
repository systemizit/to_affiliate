from odoo import fields, models, _


class AffiliateCommissionRuleLine(models.Model):
    _name = 'affiliate.commission.rule.line'
    _description = 'Affiliate Commission Rule Line'
    _order = 'sequence, rule_sequence'

    rule_id = fields.Many2one('affiliate.commission.rule', string="Commission Rule", ondelete='cascade', required=True)
    sequence = fields.Integer(string='Sequence', required=True, default=10, index=True)
    rule_sequence = fields.Integer(string='Rule Sequence', related='rule_id.sequence', store=True, index=True)
    company_id = fields.Many2one('res.company', related='rule_id.company_id', store=True, index=True)
    product_tmpl_id = fields.Many2one('product.template', string='Product', required=True, index=True)
    product_id = fields.Many2one('product.product', string="Product Variant",
                                 domain="[('product_tmpl_id', '=', product_tmpl_id)]",
                                 help="If a product variant is defined the commission is applicable only for this variant.",
                                 index=True)
    affiliate_comm_percentage = fields.Float(string="Commission Percentage (%)",
                                             default=lambda self: self.env.company.affiliate_comm_percentage,
                                             required=True)

    _sql_constraints = [
        ('product_uniq',
         'unique(product_tmpl_id,product_id,rule_id)',
         _("Product Commission Rule Line must be unique per Commission Rule!"
           " It cannot contain the same product and product template within the same rule")),
    ]
