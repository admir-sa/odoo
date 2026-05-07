{
    "name": "Shopify Odoo Bridge",
    "version": "19.0.1.0.0",
    "summary": "Pilot Shopify to Odoo order sync",
    "category": "Sales/Sales",
    "author": "ADMIR",
    "license": "LGPL-3",
    "depends": ["base", "contacts", "sale_management", "stock"],
    "data": [
        "security/ir.model.access.csv",
        "views/shopify_instance_views.xml",
        "views/shopify_order_buffer_views.xml",
        "data/ir_cron.xml"
    ],
    "installable": True,
    "application": True
}
