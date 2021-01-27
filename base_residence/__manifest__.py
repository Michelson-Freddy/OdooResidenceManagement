{
    'name': 'Base Residence Management',
    'summary': 'Base Residence Management',
    'version': '13.0.1.0.0',
    'author': "Majikat",
    'website': "https://www.hazenfield.com",
    'category': 'Base',
    'license': 'LGPL-3',
    'installable': True,
    'application': True,
    'depends': ['base'],
    'data': [
        'views/lots_views.xml',
        'views/partner_views.xml',
        'views/residence_menus.xml',
        'prints/badge.xml',
        'security/residence_security.xml',
        'security/ir.model.access.csv',
        'data/residence_cron.xml'
    ]
}
