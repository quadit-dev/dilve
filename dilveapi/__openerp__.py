# -*- coding: utf-8 -*-
{
    'name': "dilveapi",

    'summary': """
        """,

    'description': """
        Módulo de integración de DAPI.
    """,

    'author': "Quadit",
    'website': "https://www.quadit.io",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'Desarrollo',
    'version': '1.0',

    # any module necessary for this one to work correctly
    'depends': [
        'base',
        'product'
    ],

    # always loaded
    'data': [
        'security/dilveapi_security.xml',
        'security/ir.model.access.csv',
        'views/dilveapi.xml',
        'views/config.xml',
        'data/codigos.editoriales.csv',
        'data/codigos.disponibilidad.csv',
        'wizard/ws_datosLibro.xml',
        'wizard/ws_records.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}