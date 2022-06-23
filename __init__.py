from . import controllers
from . import models
from . import wizard
from . import report

from odoo import api, SUPERUSER_ID


def _update_affiliate_commission_product_default(env):
    company_ids = env['res.company'].with_context(active_test=False).search([])
    comm_product_id = env.ref('to_affiliate.to_product_product_aff_commission')
    company_ids.write({'commission_product_id': comm_product_id.id})


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _update_affiliate_commission_product_default(env)

