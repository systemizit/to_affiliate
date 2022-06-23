import string
import random

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from odoo.osv import expression


class AffiliateCode(models.Model):
    _name = 'affiliate.code'
    _inherit = ['mail.thread']
    _description = 'Affiliate Code'

    name = fields.Char(string="Code", readonly=True, tracking=True)
    active = fields.Boolean(string='Active', default=True)
    partner_id = fields.Many2one('res.partner', string="Partner", required=True, tracking=True)
    # it was saleperson_id
    salesperson_id = fields.Many2one('res.users', string="Salesperson", compute='_compute_salesperson_id',
                                     tracking=True, store=True, readonly=False,
                                     help="The salesperson who takes care of this affiliate.")
    description = fields.Html(string="Description")
    company_id = fields.Many2one('res.company', string="Company", tracking=True,
                                 default=lambda self: self.env.company, required=True)

    commission_rule_ids = fields.Many2many('affiliate.commission.rule',
                                           string='Commission Rules',
                                           help="The applicable commission rules for this affiliate code. Leave empty for auto selection"
                                           " (that selects all available rules of the selected company).")
    commission_line_ids = fields.One2many('affiliate.commission.line', 'affcode_id', string='Commissions', readonly=True)
    commission_lines_count = fields.Integer(string='Commission Lines Count', compute='_compute_commission_lines_count')
    invoice_ids = fields.Many2many('account.move', 'account_move_affiliate_code_rel', 'affcode_id', 'invoice_id', string='Client Invoices')
    invoice_count = fields.Integer(string='Client Invoices Count', compute='_compute_invoice_count')

    _sql_constraints = [
        ('partner_uniq',
         'unique(partner_id, company_id)',
         _("The selected partner already has an affiliate code for the current company!")),

        ('name_unique',
         'UNIQUE(name)',
         _("The code must be unique!")),
    ]

    def unlink(self):
        for r in self:
            if any(line.state != 'draft' for line in r.commission_line_ids):
                raise ValidationError(_("Could not delete the affiliate code '%s' that was referred by a commission whose state is not in draft!\n"
                                        "However, you could archive it or delete the corresponding the commission first.") % r.name)
        self.commission_line_ids.commission_id.unlink()
        return super(AffiliateCode, self).unlink()

    def _find_current_salesperson(self):
        self.ensure_one()
        if self.env.user.has_group('sales_team.group_sale_salesman') and not self.env.user._is_superuser():
            return self.env.user
        else:
            return False
        
    def _find_salesperson(self):
        self.ensure_one()
        return self.partner_id.user_id or self._find_current_salesperson()
    
    def _compute_commission_lines_count(self):
        commission_data = self.env['affiliate.commission.line'].read_group([('affcode_id', 'in', self.ids)], ['affcode_id'], ['affcode_id'])
        mapped_data = dict([(dict_data['affcode_id'][0], dict_data['affcode_id_count']) for dict_data in commission_data])
        for r in self:
            r.commission_lines_count = mapped_data.get(r.id, 0)
    
    @api.depends('partner_id')
    def _compute_salesperson_id(self):
        for r in self:
            r.salesperson_id = r._find_salesperson()

    def name_get(self):
        """
        name_get that supports displaying tags with their code as prefix
        """
        result = []
        for r in self:
            result.append((r.id, "%s [%s]" % (r.name, r.partner_id.name)))
        return result

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        """
        name search that supports searching by partner name
        """
        args = args or []
        domain = []
        if name:
            domain = ['|', ('partner_id.name', '=ilike', name + '%'), ('name', operator, name)]
            if operator in expression.NEGATIVE_TERM_OPERATORS:
                domain = ['&'] + domain
        codes = self.search(domain + args, limit=limit)
        return codes.name_get()

    def _get_comm_rule(self, product):
        """
        Searches for the commission rule based on the given ``product``. The priority is as below:
        1. Product Matching
        2. Product Template Matching
        3. Product Category Matching
        4. The first rule with type = 'all'
        :param product.product product: the input record of model product.product
        :returns: the most matched affiliate.commission.rule record or False
        """
        commission_rules = self.commission_rule_ids or self.env['affiliate.commission.rule'].search([
            ('company_id', '=', self.company_id.id)
            ])

        # search for the product template that corresponds to the input product
        product_tmpl_id = self.env['product.template'].search([('id', '=', product.product_tmpl_id.id)], limit=1)

        # search for commission rules that is in the type of Product template where a line of its
        # contains the product or the product's template
        product_rules = commission_rules.filtered(
            lambda rule: rule.type == 'product_tmpl' \
            and product_tmpl_id.id in [line.product_tmpl_id.id for line in rule.line_ids] \
            and (not rule.line_ids.mapped('product_id') or product in rule.line_ids.mapped('product_id'))
            )
        if product_rules:
            # return the first product matched rule
            return product_rules[0]

        product_categ_rule = commission_rules.filtered(lambda rule: rule.type == 'category' \
                                                       and product._is_child_of(rule.product_category_ids.ids))
        if product_categ_rule:
            # return the first product category matched rule
            return product_categ_rule[0]

        all_prod_rule = commission_rules.filtered(lambda r: r.type == 'all')
        if all_prod_rule:
            return all_prod_rule[0]
        return self.env['affiliate.commission.rule']

    def _get_comm_percentage(self, product):
        affiliate_comm_percentage = 0.0
        rule = self._get_comm_rule(product)
        if rule:
            affiliate_comm_percentage = rule._get_comm_percentage(product)
        return affiliate_comm_percentage, rule

    def _generate_affcode(self):
        """
        generate a string of seven random characters
        """
        return ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(7))

    @api.model
    def generate_affcode(self, excludes=[]):
        affcode = self._generate_affcode()
        if excludes and affcode in excludes:
            return self.generate_affcode(excludes)

        if self.search([('name', '=', affcode)]):
            excludes.append(affcode)
            return self.generate_affcode(excludes)

        return affcode

    @api.model_create_multi
    def create(self, vals_list):
        excludes = []
        for vals in vals_list:
            name = self.generate_affcode(excludes)
            vals['name'] = name
            excludes.append(name)
        records = super(AffiliateCode, self).create(vals_list)

        for r in records:
            subscribers = [r.partner_id.id]
            if r.salesperson_id:
                subscribers.append(r.salesperson_id.partner_id.id)
            r.message_subscribe(subscribers)
            r.partner_id.write({'supplier_rank': r.partner_id.supplier_rank + 1})
        return records

    def _compute_invoice_count(self):
        for r in self:
            r.invoice_count = len(r.invoice_ids)
    
    def action_view_commission_lines(self):
        result = self.env['ir.actions.act_window']._for_xml_id('to_affiliate.action_affiliate_com_line_tree_view')

        # get rid off the default context
        result['context'] = {}

        lines = self.mapped('commission_line_ids')
        lines_count = len(lines)
        if lines_count > 1:
            result['domain'] = "[('id', 'in', %s)]" % str(lines.ids)
        elif lines_count == 1:
            res = self.env.ref('to_affiliate.affiliate_commission_line_view_form', False)
            result['views'] = [(res and res.id or False, 'form')]
            result['res_id'] = lines.id
        else:
            result = {'type': 'ir.actions.act_window_close'}

        return result

    def action_view_client_invoices(self):
        invoices = self.mapped('invoice_ids')
        action = self.env['ir.actions.act_window']._for_xml_id('account.action_move_out_invoice_type')
        if len(invoices) > 1:
            action['domain'] = [('id', 'in', invoices.ids)]
        elif len(invoices) == 1:
            form_view = [(self.env.ref('account.view_move_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state, view) for state, view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = invoices.id
        else:
            action = {'type': 'ir.actions.act_window_close'}

        context = {
            'default_move_type': 'out_invoice',
        }
        action['context'] = context
        return action
