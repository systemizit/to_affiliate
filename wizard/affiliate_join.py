from odoo import models, fields, api, _

class WizardAffiliateJoin(models.TransientModel):
    _name = 'to.wizard.affiliate.join'
    _description = 'Wizard Affiliate Join'
    user_id = fields.Many2one('res.users', string="Affiliate User", default=lambda self: self.env.user)
    is_affiliate = fields.Boolean(string="Affiliate", related='user_id.partner_id.is_affiliate', readonly=True)
    company_id = fields.Many2one('res.company', string="Company", domain="[('aff_allowed', '=', True)]")


    @api.model
    def open_table(self):
        if not self.user_id.partner_id.is_affiliate:
            self.env['affiliate.code'].sudo().create({
                'partner_id': self.user_id.partner_id.id,
                'company_id': self.company_id and self.company_id.id or False,
            })
            return {
                'type': 'ir.actions.client',
                'tag': 'reload',
            }
        return {
                'domain': "[('partner_id', '=', " + str(self.env.user.partner_id.id) + ")]",
                'name': _('Affiliate Code'),
                'view_mode': 'tree,form',
                'res_model': 'affiliate.code',
                'type': 'ir.actions.act_window',
            }
