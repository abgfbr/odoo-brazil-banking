# -*- coding: utf-8 -*-
# Copyright 2016 KMEE - Hendrix Costa <hendrix.costa@kmee.com.br>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from __future__ import with_statement, unicode_literals


from openerp.addons.report_py3o.py3o_parser import py3o_report_extender

from openerp import api, _, exceptions

import logging
_logger = logging.getLogger(__name__)
try:
    from pybrasil import valor, data

except ImportError:
    _logger.info('Cannot import pybrasil')


@api.cr_uid_id_context
@py3o_report_extender('l10n_br_financial_payment_order.py3o_boleto_generico')
def extender_boleto_sindicato(pool, cr, uid, local_context, context):
    # companylogo = self.env['financial.move'].browse(context['active_id']).company_id.logo

    if local_context.get('active_id'):
        boleto_list = pool['financial.move'].gera_boleto(cr, uid, local_context.get('active_ids'))

        vals = {
            'boletos': boleto_list,
            # 'partner_cnpj_cpf': financial_move.partner_id.cnpj_cpf or '',
            # 'date_maturity': data.formata_data(financial_move.date_maturity),
            # 'date_document': data.formata_data(financial_move.date_document),
            # 'convenio': financial_move.payment_mode_id.convenio or '',
            # 'company_number': financial_move.company_id.number,
            # 'valor_documento':
            #     valor.formata_valor(financial_move.amount_document),
        }
        local_context.update(vals)
