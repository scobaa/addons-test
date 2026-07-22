# -*- coding: utf-8 -*-
{
    'name': 'Portal de Regularización de Asistencia',
    'version': '19.0.1.0.0',
    'category': 'Asistencias',
    'summary': 'Portal para que los empleados gestionen sus regularizaciones de asistencia',
    'description': 'Permite a los empleados con acceso portal crear, enviar y consultar solicitudes de regularización de asistencia.',
    'author': 'Tecniloop',
    'maintainer': 'Tecniloop',
    'website': 'http://www.tecniloop.es',
    'license': 'AGPL-3',
    'depends': [
        'base',
        'portal',
        'attendance_regularization',
        'dh_link_portal_employee',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/attendance_regularization_portal_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            # 'dh_attendance_regularization_portal/static/src/css/regularization_portal.css',
            'tl_attendance_regularization_portal/static/src/js/regularization_portal.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': False,
}
