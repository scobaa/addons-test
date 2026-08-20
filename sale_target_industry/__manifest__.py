# -*- coding: utf-8 -*-
# License OPL-1

{
    'name': 'Sales Targets by Industry & Period',
    'version': '19.0.1.0.0',
    'category': 'Sales/Sales',
    'summary': 'Define and track billing revenue targets by customer sector (industry), year and month with automatic computation from sales orders.',
    'description': """
Sales Targets by Industry & Period
====================================
Empower your sales leadership with automated, data-driven revenue targets
segmented by Customer Sector / Industry (`res.partner.industry`), Year, and Month.

Key Features:
-------------
* **Target Planning:** Create structured sales campaigns with target lines per industry and month.
* **100% Automated Calculation:** Computes actual achieved amount from confirmed sales orders in real-time.
* **Performance Metrics:** Automatic computation of Achievement Rate (%) and Gap amount with visual indicators.
* **Interactive Reporting:** Dedicated Pivot (matrix) and Graph (bar chart) views comparing Target vs. Achieved.
* **Manual Recalculation:** One-click header button to instantly refresh metrics.
* **Multi-Company & Multi-Currency:** Native support for multi-company isolation and company currencies.
* **Security Permissions:** Pre-configured access rights for Sales Representatives and Sales Managers.
* **Chatter Integration:** Full activity tracking and messaging.
    """,
    'author': 'Tealcloud',
    'website': 'https://tealcloud.es',
    'license': 'OPL-1',
    'price': 49.00,
    'currency': 'EUR',
    'depends': [
        'sale_management',
        'mail',
        'partner_autocomplete',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/sale_target_views.xml',
        'views/sale_target_line_views.xml',
        'views/menu_views.xml',
    ],
    'images': [
        'static/description/icon.png',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
