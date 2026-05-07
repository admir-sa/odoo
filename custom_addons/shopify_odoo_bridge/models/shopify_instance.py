import json
from datetime import timedelta

import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ShopifyInstance(models.Model):
    _name = "shopify.instance"
    _description = "Shopify Store Instance"
    _rec_name = "name"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)

    store_name = fields.Char(required=True, help="Example: offre-personnalisee-cadentia")
    shop_url = fields.Char(compute="_compute_shop_url", store=True)

    client_id = fields.Char()
    client_secret = fields.Char()
    access_token = fields.Char(copy=False)
    token_expiry = fields.Datetime(copy=False)

    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company)
    sync_active = fields.Boolean(default=True)
    last_order_sync_at = fields.Datetime()
    last_sync_message = fields.Text()

    order_buffer_count = fields.Integer(compute="_compute_order_buffer_count")

    @api.depends("store_name")
    def _compute_shop_url(self):
        for rec in self:
            rec.shop_url = f"https://{rec.store_name}.myshopify.com" if rec.store_name else False

    def _compute_order_buffer_count(self):
        for rec in self:
            rec.order_buffer_count = self.env["shopify.order.buffer"].search_count([
                ("instance_id", "=", rec.id)
            ])

    def _get_token_url(self):
        self.ensure_one()
        return f"https://{self.store_name}.myshopify.com/admin/oauth/access_token"

    def _get_orders_url(self):
        self.ensure_one()
        return f"https://{self.store_name}.myshopify.com/admin/api/2026-01/orders.json"

    def _refresh_access_token(self, force=False):
        self.ensure_one()

        if (
            not force
            and self.access_token
            and self.token_expiry
            and self.token_expiry > fields.Datetime.now() + timedelta(minutes=5)
        ):
            return self.access_token

        if not self.store_name or not self.client_id or not self.client_secret:
            raise UserError(_("Missing store name, client id, or client secret."))

        response = requests.post(
            self._get_token_url(),
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "client_credentials",
            },
            headers={
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            timeout=30,
        )

        if response.status_code >= 400:
            raise UserError(_("Shopify token error %s: %s") % (response.status_code, response.text))

        data = response.json()
        token = data.get("access_token")
        expires_in = data.get("expires_in", 0)

        if not token:
            raise UserError(_("No access token returned by Shopify."))

        self.write({
            "access_token": token,
            "token_expiry": fields.Datetime.now() + timedelta(seconds=expires_in),
            "last_sync_message": _("Token refreshed successfully."),
        })
        return token

    def action_test_token(self):
        for rec in self:
            rec._refresh_access_token(force=True)

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Shopify"),
                "message": _("Token retrieved successfully."),
                "type": "success",
                "sticky": False,
            },
        }

    def action_fetch_latest_orders(self):
        buffer_model = self.env["shopify.order.buffer"]

        for rec in self:
            token = rec._refresh_access_token()

            updated_at_min = rec.last_order_sync_at or (fields.Datetime.now() - timedelta(days=7))
            params = {
                "status": "any",
                "limit": 50,
                "updated_at_min": updated_at_min.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "fields": ",".join([
                    "id",
                    "name",
                    "created_at",
                    "updated_at",
                    "currency",
                    "email",
                    "financial_status",
                    "fulfillment_status",
                    "subtotal_price",
                    "total_discounts",
                    "total_tax",
                    "total_price",
                    "note",
                    "tags",
                    "customer",
                    "billing_address",
                    "shipping_address",
                    "line_items",
                    "shipping_lines",
                    "fulfillments",
                    "refunds",
                    "discount_codes",
                ]),
            }

            response = requests.get(
                rec._get_orders_url(),
                headers={
                    "X-Shopify-Access-Token": token,
                    "Accept": "application/json",
                },
                params=params,
                timeout=60,
            )

            if response.status_code >= 400:
                raise UserError(_("Shopify orders error %s: %s") % (response.status_code, response.text))

            payload = response.json()
            orders = payload.get("orders", [])

            for order in orders:
                existing = buffer_model.search([
                    ("instance_id", "=", rec.id),
                    ("shopify_order_id", "=", str(order.get("id"))),
                ], limit=1)

                vals = {
                    "instance_id": rec.id,
                    "shopify_order_id": str(order.get("id")),
                    "order_name": order.get("name"),
                    "raw_json": json.dumps(order, ensure_ascii=False, indent=2),
                    "sync_state": "pending",
                    "received_at": fields.Datetime.now(),
                    "processed_at": False,
                    "error_message": False,
                }

                if existing:
                    existing.write(vals)
                else:
                    buffer_model.create(vals)

            rec.write({
                "last_order_sync_at": fields.Datetime.now(),
                "last_sync_message": _("Fetched %s order(s).") % len(orders),
            })

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Shopify"),
                "message": _("Latest Shopify orders fetched into buffer."),
                "type": "success",
                "sticky": False,
            },
        }