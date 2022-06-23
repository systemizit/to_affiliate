from odoo import http, _
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.http import request


class PortalAffiliate(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super(PortalAffiliate, self)._prepare_home_portal_values(counters)
        if 'aff_commission_count' in counters:
            values.update({
                'aff_commission_count': len(request.env.user.get_affiliate_commissions()),
            })
        return values

    @http.route(['/my/affiliate/commissions', '/my/affiliate/commissions/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_affiliate_commissions(self, page=1, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        affiliate_commissions = request.env.user.get_affiliate_commissions()

        values.update({
            'affiliate_commissions': affiliate_commissions,
            'page_name': _('Affiliate Commissions'),
            'default_url': '/my/affiliate/commissions',
        })
        return request.render('to_affiliate.portal_my_affiliate', values)
