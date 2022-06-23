from odoo.tests.common import SavepointCase
from odoo import fields


class TestAffiliateCommon(SavepointCase):

    @classmethod
    def setUpClass(cls):
        super(TestAffiliateCommon, cls).setUpClass()

        cls.no_mailthread_features_ctx = {
            'no_reset_password': True,
            'tracking_disable': True,
        }
        cls.env = cls.env(context=dict(cls.no_mailthread_features_ctx, **cls.env.context))

        # groups
        cls.group_portal = cls.env.ref('base.group_portal')
        cls.group_internal = cls.env.ref('base.group_user')
        cls.group_affiliate_user = cls.env.ref('to_affiliate.group_to_affiliate_user')
        cls.group_affiliate_manager = cls.env.ref('to_affiliate.group_to_affiliate')

        cls.company_1 = cls.env['res.company'].create({
            'name': 'My Company 1',
            'currency_id': cls.env.user.currency_id.id
        })

        cls.company_2 = cls.env['res.company'].create({
            'name': 'My Company 2',
            'currency_id': cls.env.user.currency_id.id,
            'compute_aff_method': 'before_discount'
        })

        cls.user_portal = cls.env['res.users'].with_context(no_reset_password=True, tracking_disable=True).create({
            'name': 'John Wick',
            'login': 'affportal',
            'email': 'affportal@example.viindoo.com',
            'password': 'affportal',
            'groups_id': [(6, 0, [cls.group_portal.id])]
        })

        cls.user_internal = cls.env['res.users'].with_context(no_reset_password=True, tracking_disable=True).create({
            'name': 'Boom',
            'login': 'affinternal',
            'email': 'boom@example.viindoo.com',
            'groups_id': [(6, 0, [cls.group_internal.id])]
        })

        cls.user_internal_2 = cls.env['res.users'].with_context(no_reset_password=True, tracking_disable=True).create({
            'name': 'Yasuo',
            'login': 'affinternal2',
            'email': 'yasuo@example.viindoo.com',
            'groups_id': [(6, 0, [cls.group_internal.id])]
        })

        cls.user_aff = cls.env['res.users'].with_context(no_reset_password=True, tracking_disable=True).create({
            'name': 'Affiliate User',
            'login': 'affuser',
            'email': 'Jax@abc.com',
            'groups_id': [(6, 0, [cls.group_affiliate_user.id])]
        })

        cls.manager_aff = cls.env['res.users'].with_context(no_reset_password=True, tracking_disable=True).create({
            'name': 'Rich Kid',
            'login': 'affmanager',
            'email': 'rich.kid@lag.com',
            'groups_id': [(6, 0, [cls.group_affiliate_manager.id])]
        })

        # setup affiliate
        cls.commission_product = cls.env['product.product'].create({
            'name': 'Affiliate Commission',
            'type': 'service',
            'sale_ok': False,
            'purchase_ok': True,
            'list_price': 0.0,
            'standard_price': 0.0,
            'uom_id': cls.env.ref('uom.product_uom_unit').id,
            'uom_po_id': cls.env.ref('uom.product_uom_unit').id,
            'categ_id': cls.env.ref('product.product_category_all').id,
            'taxes_id': [(6, 0, [])],
            'supplier_taxes_id': [(6, 0, [])]
        })
        cls.product_1 = cls.env['product.product'].create({
            'name': '13 Pro Max',
            'lst_price': 30000000,
            'categ_id': cls.env.ref('product.product_category_all').id,
        })
        cls.product_2 = cls.env['product.product'].create({
            'name': '13 Pro',
            'lst_price': 25000000,
            'categ_id': cls.env.ref('product.product_category_all').id,
        })
        cls.product_3 = cls.env['product.product'].create({
            'name': '12 Pro',
            'lst_price': 25000000,
            'categ_id': cls.env.ref('product.product_category_all').id
        })

        cls.company_1.commission_product_id = cls.commission_product.id
        cls.company_2.commission_product_id = cls.commission_product.id

        cls.commission_rule_all = cls.env['affiliate.commission.rule'].with_context(tracking_disable=True).create({
            'name': '11%',
            'type': 'all',
            'affiliate_comm_percentage': 11.00,
            'company_id': cls.company_1.id,
        })
        cls.commission_rule_category = cls.env['affiliate.commission.rule'].with_context(tracking_disable=True).create({
            'name': '5%',
            'type': 'all',
            'affiliate_comm_percentage': 5.00,
            'company_id': cls.company_1.id,
            'product_category_ids': [(6, 0, [cls.env.ref('product.product_category_all').id])]
        })
        cls.commission_rule_product = cls.env['affiliate.commission.rule'].with_context(tracking_disable=True).create({
            'name': '3%',
            'type': 'product_tmpl',
            'company_id': cls.company_1.id,
            'line_ids': [(0, 0, {
                'product_id': cls.product_2.id,
                'product_tmpl_id': cls.product_2.product_tmpl_id.id,
                'affiliate_comm_percentage': 3.00
            })]
        })

        cls.aff_code_1 = cls.user_internal.affcode_ids[0]
        cls.aff_code_1.company_id = cls.company_1.id

        cls.aff_code_2 = cls.user_aff.affcode_ids[0]
        cls.aff_code_2.company_id = cls.company_1.id

        cls.commission = cls.env['affiliate.commission'].with_context(tracking_disable=True).create(cls.prepare_commission_data())

        cls.payment_request = cls.env['affiliate.payment'].with_context(tracking_disable=True).create({
            'partner_id': cls.user_internal.partner_id.id,
            'company_id': cls.company_1.id
        })

        cls.payment_request_2 = cls.env['affiliate.payment'].with_context(tracking_disable=True).create({
            'partner_id': cls.user_internal_2.partner_id.id,
            'company_id': cls.company_2.id
        })

    @classmethod
    def prepare_commission_lines_data(cls):
        return {
            'affiliate_commission_rule_id': cls.commission_rule_all.id,
            'product_id': cls.product_1.id,
            'currency_id': cls.company_1.currency_id.id,
            'affiliate_comm_percentage':
                cls.aff_code_1._get_comm_percentage(cls.product_1)[0],
            'total': cls.product_1.lst_price
        }

    @classmethod
    def prepare_commission_data(cls, partner=False, aff_code=None):
        return {
            'name': 'Commission 1',
            'partner_id': (partner or cls.user_aff.partner_id).id,
            'customer_id': cls.user_portal.partner_id.id,
            'affcode_id': (aff_code or cls.aff_code_2).id,
            'currency_id': cls.company_1.currency_id.id,
            'company_id': cls.company_1.id,
            'date': fields.Datetime.now(),
            'line_ids': [(0, 0, cls.prepare_commission_lines_data())],
            'state': 'confirm'
        }

    def check_commission(self, user):
        # own commission
        commission = self.env['affiliate.commission'].with_context(tracking_disable=True)\
        .with_user(user).create(self.prepare_commission_data())
        commission.read(['name'])
        commission.name = 'change comm name'
        commission.action_draft()
        commission.unlink()
        # with another commission
        commission = self.commission.with_user(self.manager_aff)
        commission.read(['name'])
        commission.name = 'change comm name'
        commission.action_draft()
        commission.unlink()

    def check_payment_request(self, user):
        # own payment request
        payment_request = self.env['affiliate.payment'].with_context(tracking_disable=True).with_user(user).create({
            'partner_id': self.user_internal.partner_id.id,
            'company_id': self.company_1.id
        })
        payment_request.read(['name'])
        payment_request.notes = 'Give me my money!'
        payment_request.action_draft()
        payment_request.unlink()

        # with another payment request
        payment_request = self.payment_request.with_user(user)
        payment_request.read(['name'])
        payment_request.notes = 'Give me my money!'
        payment_request.action_draft()
        payment_request.unlink()

    def check_commission_rule(self, user):
        commission_rule_product = self.commission_rule_product.with_user(user)
        commission_rule_product.read(['name'])
        commission_rule_product.with_context(tracking_disable=True).create({
            'name': '100%',
            'type': 'all'
        })
        commission_rule_product.description = 'Commission rule'
        commission_rule_product.unlink()
