# -*- coding: utf-8 -*-
{
    'name': 'Stock Recount Threshold',
    'version': '18.0.1.1.0',
    'category': 'Inventory/Inventory',
    'summary': 'Automated inventory recount requests triggered by low stock thresholds on stock operations',
    'description': """
Stock Recount Threshold
========================

This module allows warehouse teams to:

* Configure stock recount thresholds per product (and optionally by warehouse location).
* Automatically detect when stock moves (deliveries, internal transfers, manufacturing consumption) drop on-hand quantities below the configured threshold.
* Automatically generate formal recount requests and assign audit tasks to the designated inventory manager.
* Prevent inventory discrepancies before standard cycle counts by linking audits directly to real-time operations.

Designed specifically for fast-paced logistics and Barcode scanning workflows where waiting for scheduled cycle counts is not enough, triggering physical recounts based on actual warehouse consumption.
    """,
    'author': 'srgcba',
    'website': '',
    'price': 29.00,
    'currency': 'EUR',
    'license': 'OPL-1',
    'support': 'sergiocobaa@gmail.com',
    'depends': ['stock', 'mrp', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/product_template_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'images': ['static/description/banner.png'],
}
