from odoo import fields, models, api, _
from odoo.exceptions import UserError


class AffiliateCommission(models.Model):
    _name = 'affiliate.commission'
    _description = 'Affiliate Commission'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc'

    name = fields.Char(string="Name", required=True, readonly=True, default='/')
    partner_id = fields.Many2one('res.partner', string='Affiliate Partner', required=True, index=True)
    date = fields.Date(string="Date", required=True, readonly=True, states={'draft': [('readonly', False)]})
    currency_id = fields.Many2one('res.currency', string="Currency", required=True, readonly=True,
        states={'draft': [('readonly', False)]}, default=lambda self: self.env.company.currency_id)
    comm_amount = fields.Monetary(string="Commission Amount", currency_field='currency_id', compute='_compute_comm_amount', store=True)
    line_ids = fields.One2many('affiliate.commission.line', 'commission_id', string="Commission Details", readonly=True,
                               states={'draft': [('readonly', False)]})
    affcode_id = fields.Many2one('affiliate.code', string='Aff. Code', required=True, index=True, readonly=True)
    customer_id = fields.Many2one('res.partner', string='Customer', required=True, index=True, readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('submit', 'Payment Request'),
        ('comm_paid', 'Commission Paid'),
        ('cancel', 'Cancelled'),
    ], string="Status", default='draft', tracking=True)

    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 help="The company that will pay this commission.")
    invoice_line_ids = fields.One2many('account.move.line', 'commission_id', string='Commission Invoice Lines', readonly=True)
    invoice_ids = fields.Many2many('account.move', 'invoice_affcomm_rel', string='Invoices', readonly=True)
    invoice_ids_count = fields.Integer(string='Invoices Count', compute='_compute_invoice_ids', store=True)

    payment_request_ids = fields.Many2many('affiliate.payment', string='Payment Requests', readonly=True)

    @api.depends('invoice_ids')
    def _compute_invoice_ids(self):
        for r in self:
            r.invoice_ids_count = len(r.invoice_ids)

    @api.depends('line_ids.comm_amount')
    def _compute_comm_amount(self):
        for r in self:
            r.comm_amount = sum(x.comm_amount for x in r.line_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('affiliate.commission') or '/'
        return super(AffiliateCommission, self).create(vals_list)

    def action_confirm(self):
        self.write({'state': 'confirm'})

    def action_paid(self):
        self.write({'state': 'comm_paid'})

    def action_reopen(self):
        if self.filtered(lambda r: r.state != 'comm_paid'):
            raise UserError(_('Affiliate Commission must be paid in order to set it to Payment Request.'))
        self.write({'state':'submit'})

    def unlink(self):
        for item in self:
            if item.state not in ('draft'):
                raise UserError(_("You can only delete records whose state is draft."))
        return super(AffiliateCommission, self).unlink()

    def action_cancel(self):
        for r in self:
            if any(payment.state != 'cancel' for payment in r.payment_request_ids):
                raise UserError(_("The commission '%s' has an payment request in Confirmed or Approved or Paid status. You must delete"
                                  " or cancel all the payment request of the commission before you could cancel the commission.") % r.name)
            if any(invoice.state != 'cancel' for invoice in r.invoice_ids):
                raise UserError(_("The commission '%s' has an invoice in either Open or Paid status. You must delete"
                                  " or cancel all the invoices of the commission before you could cancel the commission.") % r.name)
        self.write({'state':'cancel'})

    def action_draft(self):
        self.write({'state':'draft'})

    def _get_commission_amount(self, date=False, company=False):
        total = 0
        for r in self:
            company = company or r.company_id
            date = date or r.date
            if r.currency_id == company.currency_id:
                total += r.comm_amount
            else:
                total += r.currency_id._convert(r.comm_amount, company.currency_id, company, date)
        return total

    def _prepare_invoice_line_data(self):
        self.ensure_one()

        company = self.env.company
        comm_product = self.company_id.commission_product_id
        expense_acc_id = comm_product.product_tmpl_id.get_product_accounts()['expense']
        if company.currency_id != self.currency_id:
            comm_amount = self.currency_id._convert(self.comm_amount, company.currency_id, company, self.date)
        else:
            comm_amount = self.comm_amount

        data = {
            'product_id': comm_product.id,
            'account_id': expense_acc_id.id,
            'name': "%s - %s" % (comm_product.display_name, self.name,),
            'price_unit': comm_amount,
            'quantity': 1.0,
            'product_uom_id': comm_product.uom_po_id.id or comm_product.product_uom_id.id,
            'commission_id': self.id,
            }
        if comm_product.supplier_taxes_id:
            data['tax_ids'] = [(6, 0, comm_product.supplier_taxes_id.ids)]
        return data
