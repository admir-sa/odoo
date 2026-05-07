from odoo import fields, models


class ShopifyOrderBuffer(models.Model):
    _name = "shopify.order.buffer"
    _description = "Shopify Order Buffer"
    _order = "id desc"

    instance_id = fields.Many2one("shopify.instance", required=True, ondelete="cascade")
    shopify_order_id = fields.Char(required=True, index=True)
    order_name = fields.Char()
    raw_json = fields.Text()
    sync_state = fields.Selection(
        [
            ("pending", "Pending"),
            ("done", "Done"),
            ("error", "Error"),
        ],
        default="pending",
        required=True,
    )
    error_message = fields.Text()
    received_at = fields.Datetime()
    processed_at = fields.Datetime()

    _sql_constraints = [
        (
            "shopify_order_instance_unique",
            "unique(instance_id, shopify_order_id)",
            "Shopify order must be unique per instance.",
        )
    ]