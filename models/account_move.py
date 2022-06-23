from odoo import fields, models, api


class AccountMove(models.Model):
    _inherit = 'account.move'
    
    affcode_ids = fields.Many2many('affiliate.code', 'account_move_affiliate_code_rel', 'invoice_id', 'affcode_id', string='Invoices',
                                   compute='_compute_affcode_ids', store=True)

    aff_payment_ids = fields.Many2many('affiliate.payment', 'aff_payment_invoice_rel', string="Commission Payment")
    commission_ids = fields.Many2many('affiliate.commission', 'invoice_affcomm_rel', string='Aff. Commission',
                                      compute='_compute_commission_ids', store=True)

    @api.depends('invoice_line_ids.affcode_id')
    def _compute_affcode_ids(self):
        for r in self:
            r.affcode_ids = [(6, 0, r.invoice_line_ids.affcode_id.ids)]

    @api.depends('invoice_line_ids', 'invoice_line_ids.commission_id')
    def _compute_commission_ids(self):
        for r in self:
            commission_ids = r.invoice_line_ids.mapped('commission_id')
            r.commission_ids = commission_ids and commission_ids.ids or False

    def action_invoice_paid(self):
        res = super(AccountMove, self).action_invoice_paid()

        # find all aff payments of self60
        aff_payment_ids = self.mapped('aff_payment_ids').filtered(lambda ap: ap.state != 'paid')

        # find aff payments to set paid
        # aff payments that have all invoices paid is considered as paid
        aff_payments_to_set_paid = self.env['affiliate.payment']
        for aff_payment_id in aff_payment_ids:
            invoice_ids = aff_payment_id.invoice_ids.filtered(lambda i: i.state == 'posted')
            if aff_payment_id.invoice_ids and all(invoice_id.payment_state == 'paid' for invoice_id in invoice_ids):
                aff_payments_to_set_paid |= aff_payment_id
        if aff_payments_to_set_paid:
            aff_payments_to_set_paid.action_paid()

        return res

    def action_invoice_re_open(self):
        res = super(AccountMove, self).action_invoice_re_open()

        paid_aff_payment_ids = self.mapped('aff_payment_ids').filtered(lambda ap: ap.state == 'paid')

        aff_payments_to_reopen = self.env['affiliate.payment']
        for aff_payment_id in paid_aff_payment_ids:
            if aff_payment_id.invoice_ids and any(invoice_id.state != 'paid' for invoice_id in aff_payment_id.invoice_ids):
                aff_payments_to_reopen |= aff_payment_id

        if aff_payments_to_reopen:
            aff_payments_to_reopen.action_reopen()

        return res
