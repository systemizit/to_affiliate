from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class AffiliateCommissionLine(models.Model):
    _name = 'affiliate.commission.line'
    _description = 'Affiliate Commission Line'
    _rec_name = 'commission_id'

    commission_id = fields.Many2one('affiliate.commission', string="Commission", required=True, index=True, ondelete='cascade', readonly=True)
    affcode_id = fields.Many2one(related='commission_id.affcode_id', store=True)
    partner_id = fields.Many2one('res.partner', related='commission_id.affcode_id.partner_id', store=True, index=True)
    customer_id = fields.Many2one(related='commission_id.customer_id', store=True, index=True)
    product_id = fields.Many2one('product.product', string="Product", readonly=True)
    total = fields.Monetary(string="Commission Base", compute='_compute_total',
                         help='Sales Value',
                         store=True)
    affiliate_comm_percentage = fields.Float(string="Commission Percentage", required=True, readonly=True, digits='Product Price')
    comm_amount = fields.Monetary(string="Commission Amount", compute='_get_amount', store=True)
    affiliate_commission_rule_id = fields.Many2one('affiliate.commission.rule', string='Commission Rule', readonly=True, index=True)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True)
    commission_product_id = fields.Many2one('product.product', related='affiliate_commission_rule_id.commission_product_id',
                                            string="Commission Product", store=True, index=True)
    state = fields.Selection(related='commission_id.state', string="Status", index=True)

    @api.constrains('partner_id', 'customer_id')
    def _check_overlap_partner_customer(self):
        for r in self:
            if r.partner_id and r.customer_id:
                if r.partner_id.id == r.customer_id.id:
                    raise ValidationError(_("The affiliate partner must not be the same as the customer in the same sales order!"))

    @api.depends('total', 'affiliate_comm_percentage')
    def _get_amount(self):
        for r in self:
            r.comm_amount = r.total * r.affiliate_comm_percentage / 100.0

    def _compute_total(self):
        for r in self:
            r.total = 0.0
            
    def _prepare_invoice_line_data(self):
        self.ensure_one()
        comm_product = self.commission_product_id or self.commission_id.company_id.commission_product_id
        expense_acc_id = comm_product.product_tmpl_id.get_product_accounts()['expense']
        data = {
            'product_id': comm_product.id,
            'account_id': expense_acc_id.id,
            'name': "%s - %s" % (comm_product.display_name, self.commission_id.name),
            'price_unit': self.comm_amount,
            'quantity': 1.0,
            'product_uom_id': comm_product.uom_po_id.id or comm_product.product_uom_id.id,
            'commission_line_id': self.id,
            'commission_id': self.commission_id.id,
            }
        if comm_product.supplier_taxes_id:
            data['tax_ids'] = [(6, 0, comm_product.supplier_taxes_id.ids)]
        return data
