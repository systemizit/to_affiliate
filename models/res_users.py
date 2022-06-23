from odoo import models, api


class ResUsers(models.Model):
    _inherit = 'res.users'
    
    @api.model_create_multi
    def create(self, vals_list):
        users = super(ResUsers, self).create(vals_list)
        users.filtered(lambda u: not u.partner_id.is_affiliate)._generate_affiliate_code()
        return users
    
    def _prepare_aff_code_vals(self):
        self.ensure_one()
        return {
            'partner_id': self.partner_id.id,
            'company_id': self.company_id.id,
            }
    
    def _generate_affiliate_code(self):
        vals_list = []
        for r in self:
            vals_list.append(r._prepare_aff_code_vals())
        return self.env['affiliate.code'].sudo().create(vals_list)

    def get_affiliate_commissions(self):
        return self.mapped('partner_id').with_context(aff_commission_state=self._context.get('aff_commission_state', False)).get_affiliate_commissions()
