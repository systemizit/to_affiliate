from odoo import fields, models, api, _
from odoo.exceptions import UserError
from odoo.tools import float_compare


class AffiliatePayment(models.Model):
    _name = 'affiliate.payment'
    _description = 'Affiliate Payment'
    _inherit = ['mail.thread']

    name = fields.Char(string="Name", required=True, readonly=True, default='/')
    partner_id = fields.Many2one('res.partner', string="Affiliate", required=True,
                              tracking=True, readonly=True, states={'draft': [('readonly', False)]},
                              default=lambda self: self.env.user.partner_id)
    date = fields.Date(string="Payment Date", required=True, readonly=True,
                       states={'draft': [('readonly', False)]}, default=fields.Date.today)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    company_currency_id = fields.Many2one('res.currency', related="company_id.currency_id", string="Company Currency")
    total = fields.Monetary(string="Commission Total", currency_field='company_currency_id',
                         compute='_compute_total', store=True)
    reference = fields.Char(string="Reference", readonly=True, states={'draft': [('readonly', False)]})
    notes = fields.Text(string="Notes")
    com_ids = fields.Many2many('affiliate.commission',
                               string="Commission", domain="[('state','=','confirm')]", readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed by Affiliate'),
        ('approve', 'Approved'),
        ('paid', 'Paid'),
        ('cancel', 'Rejected'),
    ], string="Status", default='draft', tracking=True)
    invoice_ids = fields.Many2many('account.move', 'aff_payment_invoice_rel', compute='_compute_invoice_ids', store=True, string="Invoices")
    invoice_ids_count = fields.Integer(string='Invoices Count', compute='_compute_invoice_ids_count', store=True)

    @api.depends('com_ids.comm_amount')
    def _compute_total(self):
        for r in self:
            r.total = r.com_ids._get_commission_amount(r.date, r.company_id)

    @api.depends('com_ids', 'com_ids.invoice_ids')
    def _compute_invoice_ids(self):
        for r in self:
            invoice_ids = r.com_ids.mapped('invoice_ids')
            r.invoice_ids = invoice_ids.ids

    @api.depends('invoice_ids')
    def _compute_invoice_ids_count(self):
        for r in self:
            r.invoice_ids_count = len(r.invoice_ids)

    def action_compute(self):
        AffCommission = self.env['affiliate.commission']
        for r in self:
            if r.partner_id and r.date:
                company = r.company_id or self.env.company
                commission_ids = AffCommission.search([
                    ('partner_id', '=', r.partner_id.id),
                    ('date', '<=', r.date),
                    ('state', '=', 'confirm'),
                    ('company_id', '=', company.id)
                ])
                if commission_ids:
                    r.write({'com_ids': [(6, 0, commission_ids.ids)]})
        return True

    def action_confirm(self):
        precision = self.env['decimal.precision'].precision_get('Product Price')
        self.action_compute()
        for r in self:
            if not r.com_ids:
                raise UserError(_("You can not submit a payment request which has no commission."))

            affiliate_min_payout = r.company_id.affiliate_min_payout or 0.0
            if float_compare(r.total, affiliate_min_payout, precision_digits=precision) == -1:
                raise UserError(_("Your Unpaid Commission so far is %s while the minimum payout is %s."
                                  " You need to make additional %s before you can request for commission payment")
                                  % (r.total, affiliate_min_payout, affiliate_min_payout - r.total))

        self.write({'state': 'confirm'})
        self.com_ids.write({'state':'submit'})

    def _prepare_invoice_data(self):
        self.ensure_one()

        invoice_lines = []
        for comm in self.com_ids:
            invoice_lines.append((0, 0, comm._prepare_invoice_line_data()))

        return {
            'partner_id': self.partner_id.id,
            'date': self.date,
            'invoice_date': self.date,
            'move_type': 'in_invoice',
            'invoice_line_ids': invoice_lines,
            'currency_id': self.env.company.currency_id.id,
            'company_id': self.env.company.id
            }

    def action_create_invoices(self):
        invoice_ids = self.env['account.move']

        for r in self:
            commission_product_id = r.company_id.commission_product_id or self.env.company.commission_product_id
            if not commission_product_id:
                raise UserError(_("You must configure Commission Product before approving payment."))

            invoice_data = r._prepare_invoice_data()
            new_invoice = invoice_ids.create(invoice_data)
            invoice_ids += new_invoice

        return invoice_ids

    def action_approve(self):
        self.action_create_invoices()
        self.write({'state': 'approve'})

    def action_paid(self):
        self.write({'state': 'paid'})
        self.mapped('com_ids').action_paid()

    def action_reopen(self):
        if self.filtered(lambda r: r.state != 'paid'):
            raise UserError(_('Affiliate Payment must be paid in order to set it to Approved.'))

        self.write({'state': 'approve'})
        self.mapped('com_ids').filtered(lambda r: r.state == 'comm_paid').action_reopen()

    def action_view_invoice(self):
        invoice_ids = self.mapped('invoice_ids')
        action = self.env['ir.actions.act_window']._for_xml_id('account.action_move_out_invoice_type')
        if len(invoice_ids) > 1:
            action['domain'] = [('id', 'in', invoice_ids.ids)]
        elif len(invoice_ids) == 1:
            action['views'] = [(self.env.ref('account.view_move_form').id, 'form')]
            action['res_id'] = invoice_ids.ids[0]
        else:
            action = {'type': 'ir.actions.act_window_close'}

        return action

    def action_cancel(self):
        draft_invoices = self.mapped('invoice_ids').filtered(lambda inv: inv.state == 'draft')
        if draft_invoices:
            draft_invoices.unlink()
        non_draft_invoices = self.mapped('invoice_ids') - draft_invoices
        if non_draft_invoices:
            for invoice in non_draft_invoices:
                if invoice.payment_state in ['in_payment', 'paid']:
                    raise UserError(_("You cannot reject the affiliate payment '%s' that has been linked to a reconciled invoice. "
                                                "Please unreconcile invoice '%s' before rejecting it.") % (self.name, invoice.name))
            non_draft_invoices.button_cancel()
        self.write({'state': 'cancel'})
        self.com_ids.write({'state':'confirm'})

    def action_draft(self):
        self.write({'state': 'draft'})

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('affiliate.payment') or '/'
        return super(AffiliatePayment, self).create(vals_list)

    def unlink(self):
        for item in self:
            if item.state not in ('draft'):
                raise UserError(_("You can only delete records whose state is draft."))
        return super(AffiliatePayment, self).unlink()
