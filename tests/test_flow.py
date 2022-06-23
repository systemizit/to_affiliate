from psycopg2 import IntegrityError

from odoo.exceptions import UserError, ValidationError
from odoo.tools import mute_logger
from odoo.tests import tagged

from .test_common import TestAffiliateCommon


@tagged('post_install', '-at_install')
class TestFlow(TestAffiliateCommon):

    def test_affcode_unique_partner_company(self):
        with mute_logger('odoo.sql_db'):
            with self.assertRaises(IntegrityError):
                self.aff_code_1.copy()
                self.env['affiliate.code'].with_context(tracking_disable=True).create({
                    'partner_id': self.user_internal.partner_id.id,
                    'company_id': self.company_1.id
                })

    def test_create_affcode(self):
        # auto gen code when creating user
        user_portal = self.env['res.users'].with_context(no_reset_password=True, tracking_disable=True).create({
            'name': 'Tran Dan',
            'login': 'trandan',
            'groups_id':  [(6, 0, [self.group_portal.id])]
        })
        self.assertTrue(user_portal.partner_id.affcode_ids)
        user_internal = self.env['res.users'].with_context(no_reset_password=True, tracking_disable=True).create({
            'name': 'Zed',
            'login': 'zed@rito.com',
            'groups_id': [(6, 0, [self.group_internal.id])]
        })
        self.assertTrue(user_internal.partner_id.affcode_ids)

        # duplicate user
        user_portal_copy = user_portal.copy()
        self.assertTrue(user_portal_copy.partner_id.affcode_ids)

        # remove and re-create
        user_portal_copy.partner_id.affcode_ids.unlink()
        self.env['affiliate.code'].with_context(tracking_disable=True).create({
            'partner_id': user_portal_copy.partner_id.id
        })

        # create affcode with partner first
        partner_1 = self.env['res.partner'].with_context(context_no_mail = {
            'no_reset_password': True,
            'mail_create_nosubscribe': True,
            'mail_create_nolog': True}).create({
            'name': 'Partner Pim'
        })
        affcode_partner_1 = self.env['affiliate.code'].with_context(tracking_disable=True).create({
            'partner_id': partner_1.id
        })
        # then create user later
        user_with_partner_1 = self.env['res.users'].with_context(no_reset_password=True, tracking_disable=True).create({
            'login': 'pim',
            'partner_id': partner_1.id,
            'groups_id': [(6, 0, [self.group_portal.id])]
        })
        self.assertEqual(user_with_partner_1.partner_id.affcode_ids, affcode_partner_1)

    def test_01_remove_partner_has_been_linked_to_affiliate_code(self):
        """Test: remove partner has been linked to affiliate code
        And affiliate code has been linked to commission whose state is in draft"""
        partner_1 = self.env['res.partner'].with_context(context_no_mail = {
            'no_reset_password': True,
            'mail_create_nosubscribe': True,
            'mail_create_nolog': True}).create({
            'name': 'Partner Pim'
        })
        affcode_partner_1 = self.env['affiliate.code'].with_context(tracking_disable=True).create({
            'partner_id': partner_1.id
        })
        # Can delete
        partner_1.unlink()

    def test_02_remove_partner_has_been_linked_to_affiliate_code(self):
        """Test: remove partner has been linked to affiliate code
        And affiliate code has been linked to commission whose state is not in draft"""
        partner_1 = self.env['res.partner'].with_context(context_no_mail = {
            'no_reset_password': True,
            'mail_create_nosubscribe': True,
            'mail_create_nolog': True}).create({
            'name': 'Partner Pim'
        })
        affcode_partner_1 = self.env['affiliate.code'].with_context(tracking_disable=True).create({
            'partner_id': partner_1.id
        })

        vals = self.prepare_commission_data(partner=partner_1, aff_code=affcode_partner_1)
        commission = self.env['affiliate.commission'].with_context(tracking_disable=True).create(vals)

        self.assertNotEqual(commission.state, 'draft')
        # Cannot delete
        with self.assertRaises(ValidationError):
            partner_1.unlink()
        # Can delete
        commission.state = 'draft'
        self.assertEqual(commission.state, 'draft')
        partner_1.unlink()

    def test_default_commission_percentage(self):
        commission_rule = self.env['affiliate.commission.rule'].with_context(tracking_disable=True).create({
            'name': 'Rule Test',
            'type': 'all'
        })
        self.assertEqual(commission_rule.affiliate_comm_percentage, self.company_1.affiliate_comm_percentage)

    def test_remove_commission_state_not_in_draft(self):
        self.commission.state = 'confirm'
        with self.assertRaises(UserError):
            self.commission.unlink()

    def test_cancel_commission__invoice_paid(self):
        self.commission.line_ids.total = self.product_1.lst_price
        self.payment_request.partner_id = self.user_aff.partner_id.id
        self.payment_request.action_confirm()
        self.payment_request.action_approve()
        invoice = self.payment_request.invoice_ids.filtered(lambda i: i.state != 'cancel')[:1]
        invoice.action_invoice_paid()
        # cancel commission when it has invoice already paid => Error
        with self.assertRaises(UserError):
            self.commission.action_cancel()

    def test_remove_payment_request_state_not_in_draft(self):
        self.payment_request.state = 'confirm'
        with self.assertRaises(UserError):
            self.payment_request.unlink()

    def test_submit_payment_request(self):
        # no commission
        with self.assertRaises(UserError):
            self.payment_request_2.action_confirm()
        # with commission lines
        self.commission.line_ids.total = self.product_1.lst_price
        self.payment_request.partner_id = self.user_aff.partner_id.id
        self.payment_request.action_confirm()
        self.assertEqual(len(self.payment_request.com_ids), 1)

        # change percentage rule => do not change commission amount previously created
        amount = self.payment_request.com_ids.comm_amount
        self.commission_rule_all.affiliate_comm_percentage = 3
        self.payment_request.com_ids.flush(['comm_amount'])
        self.assertEqual(self.payment_request.com_ids.comm_amount, amount)

    def test_submit_payment_minpayout_commission(self):
        # commision amount < min payout => submit payment
        self.company_1.affiliate_min_payout = 10000000000
        with self.assertRaises(UserError):
            self.payment_request.action_confirm()

    def test_payment_invoice(self):
        # gen invoice when submit
        self.assertEqual(self.payment_request.invoice_ids_count, 0)
        self.commission.line_ids.total = self.product_1.lst_price
        self.payment_request.partner_id = self.user_aff.partner_id.id
        self.payment_request.action_confirm()
        self.payment_request.action_approve()
        self.assertEqual(self.payment_request.invoice_ids_count, 1)

        # check product in invoice lines = product commission
        invoice_lines = self.payment_request.invoice_ids.filtered(lambda i: i.state != 'cancel').invoice_line_ids
        self.assertEqual(invoice_lines.mapped('product_id'), self.commission_product)

        self.assertEqual(sum(invoice_lines.mapped('price_unit')), self.payment_request.total)

        # cancel payment request => invoice also removed
        self.payment_request.action_cancel()
        self.assertEqual(self.payment_request.invoice_ids_count, 0)

    def test_invoice_paid(self):
        self.commission.line_ids.total = self.product_1.lst_price
        self.payment_request.partner_id = self.user_aff.partner_id.id
        self.payment_request.action_confirm()
        self.payment_request.action_approve()
        invoice = self.payment_request.invoice_ids.filtered(lambda i: i.state != 'cancel')[:1]
        invoice.action_invoice_paid()
        # invoice paid => update state payment and commission is paid
        self.assertEqual(self.payment_request.state, 'paid')
        self.assertEqual(self.payment_request.com_ids.mapped('state'), ['comm_paid'])
