from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    affcode_id = fields.Many2one('affiliate.code', string='Affiliate Code', readonly=True,
                                 help="Indicate if this line was generated from"
                                 " a sale order line related to sales referred by an affiliate.")
    commission_line_id = fields.Many2one('affiliate.commission.line', string='Affiliate Commission Line', readonly=True)
    commission_id = fields.Many2one(related='commission_line_id.commission_id', string='Affiliate Commission', store=True)

    @api.constrains('currency_id', 'commission_id')
    def _check_invoice_line_currency(self):
        for r in self.filtered(lambda line: line.commission_id and line.currency_id):
            if r.currency_id != r.commission_id.currency_id:
                raise ValidationError(_("Currency of invoice list must be the same with currency of commission (%s)!")
                                      % r.commission_id.currency_id.name)
