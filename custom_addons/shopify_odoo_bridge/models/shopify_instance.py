from odoo import api, fields, models


class ShopifyInstance(models.Model):
    _name = "shopify.instance"
    _description = "Shopify Store Instance"
    _rec_name = "name"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)

    store_name = fields.Char(required=True)
    client_id = fields.Char()
    client_secret = fields.Char()
    access_token = fields.Char(copy=False)
    token_expiry = fields.Datetime(copy=False)

    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company)
    sync_active = fields.Boolean(default=True)
    last_order_sync_at = fields.Datetime()
    last_sync_message = fields.Text()

    order_buffer_count = fields.Integer(compute="_compute_order_buffer_count")

    @api.depends()
    def _compute_order_buffer_count(self):
        for rec in self:
            rec.order_buffer_count = self.env["shopify.order.buffer"].search_count([
                ("instance_id", "=", rec.id)
            ])
