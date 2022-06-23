from odoo import tools
from odoo import fields, models, api


class AffiliateReferrerAnalysis(models.Model):
    _name = 'report.affiliate.referrer.analysis'
    _description = 'Affiliate Referrer Analysis'
    _auto = False

    affcode_id = fields.Many2one('affiliate.code', string="Affiliate Code", readonly=True)
    affiliate_id = fields.Many2one('res.partner', string="Affiliate", readonly=True)
    referrer = fields.Char(string="Referrer", readonly=True)
    ip = fields.Char(string="IP Address", readonly=True)
    browser = fields.Char(string="Browser", readonly=True)
    datetime = fields.Datetime(string="Datetime", readonly=True)

    def _select(self):
        return """
            SELECT
                min(a.id) as id,
                affcode_id,
                ac.partner_id as affiliate_id,
                referrer,
                ip,
                browser,
                datetime
        """

    def _from(self):
        return """
            FROM affiliate_referrer AS a
            LEFT JOIN affiliate_code AS ac ON a.affcode_id = ac.id
        """

    def _where(self):
        return """
            WHERE a.id != 0
        """

    def _group_by(self):
        return """
        GROUP BY
            affcode_id,
            ac.partner_id,
            referrer,
            ip,
            browser,
            datetime
        """

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (
            %s
            %s
            %s
            %s
            )
        """ % (self._table, self._select(), self._from(), self._where(), self._group_by()))
