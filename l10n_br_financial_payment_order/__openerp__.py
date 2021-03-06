# -*- coding: utf-8 -*-
# Copyright 2017 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'L10n Br Financial Payment Order',
    'summary': """
        Integracao entre o modulo financeiro e a ordem de pagamento""",
    'version': '8.0.1.0.0',
    'license': 'AGPL-3',
    'author': 'KMEE,Odoo Community Association (OCA)',
    'website': 'www.kmee.com.br',
    'external_dependencies': {
        'python': [
            'pyboleto',
        ],
    },
    'depends': [
        'account_banking_payment_export',
        'l10n_br_account_product',
        'financial',
        'report_py3o',
        'l10n_br_hr_payroll',
    ],
    'data': [
        'wizards/ordem_pagamento_holerite_wizard.xml',
        'wizards/l10n_br_payment_cnab.xml',
        'views/payment_menu.xml',
        'views/bank_payment_line.xml',
        'views/financial_move.xml',

        'views/inherited_financial_document_type_view.xml',
        'views/inherited_financial_move_debt_2pay_view.xml',

        'views/payment_mode/payment_mode_base_view.xml',
        'views/payment_mode/payment_mode_pagamento_view.xml',
        'views/payment_mode/payment_mode_cobranca_view.xml',

        'views/payment_order/payment_order_base_view.xml',
        'views/payment_order/payment_order_cobranca_view.xml',
        'views/payment_order/payment_order_pagamento_view.xml',

        'views/financial_retorno_bancario.xml',
        'views/financial_move.xml',
        'workflows/payment_order_workflow.xml',

        'reports/report_boleto.xml',
        'reports/py3o_boleto.xml',
        'reports/py3o_boleto_sindicato.xml',
        'reports/py3o_darf.xml',
        'reports/py3o_gps.xml',
        # 'security/payment_mode.xml',
        # 'security/payment_mode_type.xml',
        # 'security/bank_payment_line.xml',
        # 'security/payment_line.xml',
        # 'security/payment_order.xml',

        # 'views/payment_mode.xml',
        # 'views/payment_mode_type.xml',
        # 'views/bank_payment_line.xml',
        # 'views/payment_line.xml',
    ],
    'demo': [
        # 'demo/payment_mode.xml',
        # 'demo/payment_mode_type.xml',
        # 'demo/bank_payment_line.xml',
        # 'demo/payment_order.xml',
    ],
}
