from odoo import fields, models


class AffiliateReferrer(models.Model):
    _name = 'affiliate.referrer'
    _description = 'Affiliate Referrer'

    affcode_id = fields.Many2one('affiliate.code', string="Affiliate Code", required=True, index=True)
    partner_id = fields.Many2one('res.partner', related='affcode_id.partner_id', store=True, index=True)
    name = fields.Char(string="Name", required=True, index=True)
    referrer = fields.Char(string="Source", index=True)
    ip = fields.Char(string="IP Address", index=True)
    browser = fields.Char(string="Browser", index=True)
    datetime = fields.Datetime(string="Datetime", default=fields.Datetime.now, required=True, index=True)
