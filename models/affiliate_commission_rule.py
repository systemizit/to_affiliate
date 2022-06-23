from odoo import fields, models, api


class AffiliateCommissionRule(models.Model):
    _name = 'affiliate.commission.rule'
    _description = 'Affiliate Commission Rule'
    _inherit = ['mail.thread']
    _order = 'sequence'

    name = fields.Char(string="Rule Name", required=True)
    sequence = fields.Integer(string='Sequence', required=True, default=10)
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company,
                                 index=True, tracking=True)
    type = fields.Selection([
        ('all', 'All Products'),
        ('category', 'Product Categories'),
        ('product_tmpl', 'Products'),
    ], string="Applied to", required=True, default='category', tracking=True)
    affiliate_comm_percentage = fields.Float(string="Commission Percentage", default=lambda self: self.env.company.affiliate_comm_percentage,
                                tracking=True)
    product_category_ids = fields.Many2many('product.category', string="Product Categories")
    description = fields.Text(string="Description")
    line_ids = fields.One2many('affiliate.commission.rule.line', 'rule_id', string="Commission Details", copy=True, compute='_compute_line_ids', readonly=False, store=True)

    commission_product_id = fields.Many2one('product.product', string="Commission Product", required=True,
                                     domain=[('type', '=', 'service')],
                                     default=lambda self: self.env.company.commission_product_id,
                                     help="The product that presenting affiliate commission for this rule",
                                     tracking=True)

    @api.depends('type')
    def _compute_line_ids(self):
        for r in self:
            org_line_ids = r._origin and r._origin.line_ids or False
            if r.type not in ('product', 'product_tmpl'):
                r.line_ids = False
            else:
                r.line_ids = org_line_ids

    def _get_rule_line(self, product_tmpl, product):
        LineSudo = self.env['affiliate.commission.rule.line'].sudo()
        line = LineSudo.search([
            ('id', 'in', self.line_ids.ids),
            ('product_tmpl_id', '=', product_tmpl.id),
            ('product_id', '=', product.id)], limit=1)
        if not line:
            line = LineSudo.search([
                ('id', 'in', self.line_ids.ids),
                ('product_tmpl_id', '=', product_tmpl.id)], limit=1)

        return line or self.env['affiliate.commission.rule.line']

    def _get_comm_percentage(self, product):
        """
        Get the commission percentage of the commission rule. The priority is as below:
        1. If the rule is product/product template based,
        1.1. return the most matched line's percentage
        1.2. return the rule percentage if no matched line found
        2. Return the rule's percentage
        """
        affiliate_comm_percentage = 0.0
        if self.type == 'product_tmpl':
            product_tmpl = self.env['product.template'].search([('id', '=', product.product_tmpl_id.id)], limit=1)
            line = self._get_rule_line(product_tmpl, product)
            if line:
                affiliate_comm_percentage = line.affiliate_comm_percentage
        elif self.type == 'category':
            if product._is_child_of(self.product_category_ids.ids):
                affiliate_comm_percentage = self.affiliate_comm_percentage
        else:
            affiliate_comm_percentage = self.affiliate_comm_percentage

        return affiliate_comm_percentage
