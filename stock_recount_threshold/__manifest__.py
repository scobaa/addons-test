# -*- coding: utf-8 -*-
{
    'name': 'Stock Recount Threshold',
    'version': '19.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Dispara automáticamente una solicitud de recuento cuando el '
                'stock de un producto cruza un umbral configurable tras un '
                'picking o consumo de fabricación.',
    'description': """
Stock Recount Threshold
========================

Este módulo permite:

* Configurar un umbral de cantidad por producto (y opcionalmente por ubicación).
* Detectar automáticamente cuándo un movimiento de stock (picking, entrega,
  consumo de fabricación) deja la cantidad disponible por debajo de ese umbral.
* Crear una actividad de recuento asignada al responsable de inventario,
  o directamente un ajuste de inventario (stock.inventory) listo para revisar.

Pensado para flujos donde se trabaja con la app de Códigos de Barras y no
se quiere confiar en recuentos cíclicos programados por fecha, sino en
recuentos disparados por actividad real de picking/consumo.
    """,
    'author': 'Tu nombre / Tu consultora',
    'website': '',
    'license': 'LGPL-3',
    'depends': ['stock', 'mrp'],
    'data': [
        'security/ir.model.access.csv',
        'views/product_template_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
