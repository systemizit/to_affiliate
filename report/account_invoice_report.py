# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AccountInvoiceReport(models.Model):
    _inherit = "account.invoice.report"

    affcode_id = fields.Many2one('affiliate.code', string='Affiliate Code', readonly=True)
    affiliate_partner_id = fields.Many2one('res.partner', string='Affiliate Partner', readonly=True)
    commission_id = fields.Many2one('affiliate.commission', string='Affiliate Commission', readonly=True)

    @api.model
    def _select(self):
        sql = super(AccountInvoiceReport, self)._select()
        sql += ''',
                afcode.id AS affcode_id,
                afcode.partner_id AS affiliate_partner_id,
                afcomm.id AS commission_id
        '''
        return sql

    @api.model
    def _from(self):
        sql = super(AccountInvoiceReport, self)._from()
        sql += '''
            LEFT JOIN affiliate_code AS afcode ON afcode.id = line.affcode_id
            LEFT JOIN affiliate_commission AS afcomm ON afcomm.id = line.commission_id
        '''
        return sql

    @api.model
    def _group_by(self):
        sql = super(AccountInvoiceReport, self)._group_by()
        sql += ''',
                afcode.id,
                afcomm.id
        '''
        return sql

