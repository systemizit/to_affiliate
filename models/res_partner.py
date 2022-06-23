from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_affiliate = fields.Boolean(string="Is Affiliate", default=False,
                                  compute='_compute_is_affiliate', store=True, index=True, compute_sudo=True)
    affcode_ids = fields.One2many('affiliate.code', 'partner_id', string="Affiliate Code")

    @api.depends('affcode_ids')
    def _compute_is_affiliate(self):
        affcode_data = self.env['affiliate.code'].read_group([('partner_id', 'in', self.ids)], ['partner_id'], ['partner_id'])
        mapped_data = dict([(dict_data['partner_id'][0], dict_data['partner_id_count']) for dict_data in affcode_data])
        for r in self:
            if mapped_data.get(r.id, 0) > 0:
                r.is_affiliate = True
            else:
                r.is_affiliate = False

    def unlink(self):
        for r in self:
            if any(line.state != 'draft' for line in r.affcode_ids.commission_line_ids):
                raise ValidationError(_("Could not delete the partner '%s' that was referred by a commission whose state is not in draft!\n"
                                        "However, you could archive it or delete the corresponding the commission first.") % r.name)
        self.affcode_ids.unlink()
        return super(ResPartner, self).unlink()

    def get_affiliate_commissions(self):
        state = self._context.get('aff_commission_state', False)
        domain = [('partner_id', 'in', self.ids)]
        if state:
            domain += [('state', '=', state)]
        return self.env['affiliate.commission'].search(domain)
