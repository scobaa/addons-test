# -*- coding: utf-8 -*-
# License OPL-1

{
    'name': 'Sales Targets by Industry & Period',
    'version': '19.0.1.0.0',
    'summary': 'Define and track sales targets broken down by customer industry, year and month.',
    'description': """
Sales Targets by Industry & Period
====================================
Allows sales managers to define billing targets broken down by:
- Customer Sector / Industry (res.partner.industry)
- Year and Month

Automatically calculates the achieved amount from confirmed sales orders
and computes the achievement rate percentage.

Features:
- Target Plan (header) with editable target lines (table view)
- Pivot and Graph views for comparing target vs achieved by industry and month
- Manual recalculation button on the target plan header
- Accessible from Sales > Reporting > Targets by Industry
    """,
    'author': 'Tealcloud',
    'category': 'Sales/Sales',
    'license': 'OPL-1',
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
    'installable': True,
    'application': False,
    'auto_install': False,
}
