from odoo.exceptions import AccessError
from odoo.tests import tagged

from .test_common import TestAffiliateCommon


@tagged('post_install', '-at_install')
class TestAccessRights(TestAffiliateCommon):

    # PORTAL USER
    def test_portal_user_access_affcode(self):
        # Case: Portal User read affiliate code
        # Result: Success
        portal_affcode = self.user_portal.affcode_ids[0].with_user(self.user_portal)
        internal_affcode = self.user_internal.affcode_ids[0].with_user(self.user_portal)
        portal_affcode.read(['name'])
        internal_affcode.read(['name'])
        # Case: Portal User create, write, delete affiliate code
        # Result: AccessError
        with self.assertRaises(AccessError):
            self.env['affiliate.code'].with_context(tracking_disable=True).with_user(self.user_portal).create({
                'partner_id': self.user_portal.partner_id.id,
                'company_id': self.company_2.id
            })
            portal_affcode.write({
                'description': 'My code description'
            })
            portal_affcode.unlink()
            internal_affcode.write({
                'description': 'My code description'
            })
            internal_affcode.unlink()

    def test_user_portal_access_commission(self):
        # Case: Portal User create, read, write, unlink payment request
        # Result: AccessError
        with self.assertRaises(AccessError):
            self.check_commission_rule(self.user_portal)

    def test_user_portal_access_aff_payment(self):
        # Case: Portal User create, write, unlink payment request
        # Result: AccessError
        with self.assertRaises(AccessError):
            self.check_payment_request(self.user_portal)

    def test_user_portal_access_commission_rule(self):
        # Case: Portal User create, write, unlink commission rule
        # Result: AccessError
        commission_product = self.commission_product.with_user(self.user_portal)
        with self.assertRaises(AccessError):
            commission_product.read([])
            commission_product.with_context(tracking_disable=True).create({
                'name': '100%',
                'type': 'all'
            })
            commission_product.description = 'Commission rule'
            commission_product.unlink()

    # USER AFFILIATE
    def test_useraff_access_affcode(self):
        # Case: User Affiliate create, write, unlink affiliate code
        # Result: AccessError
        with self.assertRaises(AccessError):
            affcode_affuser = self.env['affiliate.code'].with_context(tracking_disable=True).with_user(self.user_aff).create({
                'partner_id': self.user_internal_2.partner_id.id,
                'company_id': self.company_2.id
            })
            affcode_affuser.write({
                'description': 'My code description'
            })
            affcode_affuser.unlink()

    def test_useraff_access_commission(self):
        # Case: User Affiliate create, write, unlink commission
        # Result: Success
        self.check_commission(self.user_aff)

    def test_useraff_access_aff_payment(self):
        # Case: User Affiliate create, write, unlink payment request
        # Result: Success
        self.check_payment_request(self.user_aff)

    def test_useraff_access_comission_rule(self):
        # Case: User Affiliate create, write, unlink commission rule
        # Result: AccessError
        with self.assertRaises(AccessError):
            self.check_commission_rule(self.user_aff)

    # MANAGER
    def test_affiliate_manager_access_affcode(self):
        # Case: Affiliate Manager create, write, unlink affiliate code
        # Result: Success

        # remove all affcode before test
        self.user_portal.partner_id.affcode_ids.unlink()
        self.user_portal.partner_id.flush(['affcode_ids'])
        own_aff_code = self.env['affiliate.code'].with_context(tracking_disable=True).with_user(self.manager_aff).create({
            'partner_id': self.user_portal.partner_id.id,
        })
        own_aff_code.read([])
        own_aff_code.description = 'OK'
        own_aff_code.unlink()
        # with another affcode
        another_aff_code = self.user_internal_2.partner_id.affcode_ids[:1].with_user(self.manager_aff)
        another_aff_code.read([])
        another_aff_code.description = 'OK',
        another_aff_code.unlink()

    def test_affiliate_manager_access_commission(self):
        # Case: Affiliate Manager create, write, unlink commission
        # Result: Success
        self.check_commission(self.manager_aff)

    def test_affiliate_manager_access_affpayment(self):
        # Case: Affiliate Manager create, write, unlink payment request
        # Result: Success
        self.check_payment_request(self.manager_aff)

    def test_affiliate_manager_access_commission_rule(self):
        # Case: Affiliate Manager create, write, unlink commission rule
        # Result: Success
        self.check_commission_rule(self.manager_aff)
