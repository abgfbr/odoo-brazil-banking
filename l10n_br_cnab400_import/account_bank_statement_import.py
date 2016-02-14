# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Fernando Marcato Rodrigues
#    Copyright (C) 2015 KMEE - www.kmee.com.br
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import logging
import StringIO
from openerp import api, models, fields
from openerp.tools.translate import _
from openerp.exceptions import Warning
from .file_cnab400_parser import Cnab400Parser as cnabparser


_logger = logging.getLogger(__name__)


MODOS_IMPORTACAO_CNAB = [
    ('bradesco_cobranca_400', u'Bradesco Cobrança 400'),
]


class AccountBankStatementImport(models.TransientModel):
    """  """
    _inherit = 'account.bank.statement.import'

    import_modes = fields.Selection(
        MODOS_IMPORTACAO_CNAB,
        string=u'Opções de importação', select=True, required=True)

    @api.model
    def _check_cnab(self, data_file):
        if cnabparser is None:
            return False
        try:
            cnab_file = cnabparser.parse(StringIO.StringIO(data_file))
        except:
            return False
        return cnab_file

    @api.model
    def _find_bank_account_id(self, account_number):
        """ Get res.partner.bank ID """
        bank_account_id = None
        if account_number:
            bank_account_ids = self.env['res.partner.bank'].search(
                [('acc_number', '=', str(account_number))], limit=1)
            if bank_account_ids:
                bank_account_id = bank_account_ids[0].id
        return bank_account_id

    @api.model
    def _complete_statement(self, stmt_vals, journal_id, account_number):
        """Complete statement from information passed.
            unique_import_id can be imported more than 1 time."""
        stmt_vals['journal_id'] = journal_id

        #TODO pesquisar cnpj do parceiro para a reconciliação
        for line_vals in stmt_vals['transactions_cnab_return']:
            # write on move_line
            self.write_data_on_move_line(line_vals)
            pass

        for line_vals in stmt_vals['transactions']:
            self.write_data_on_paid_move_line(line_vals)
            unique_import_id = line_vals.get('unique_import_id', False)
            if unique_import_id:
                line_vals['unique_import_id'] = unique_import_id
            if not line_vals.get('bank_account_id'):
                # Find the partner and his bank account or create the bank
                # account. The partner selected during the reconciliation
                # process will be linked to the bank when the statement is
                # closed.
                partner_id = False
                bank_account_id = False
                partner_account_number = line_vals.get('account_number')
                if partner_account_number:
                    bank_model = self.env['res.partner.bank']
                    banks = bank_model.search(
                        [('acc_number', '=', partner_account_number)], limit=1)
                    if banks:
                        bank_account_id = banks[0].id
                        partner_id = banks[0].partner_id.id
                    else:
                        bank_obj = self._create_bank_account(
                            partner_account_number)
                        bank_account_id = bank_obj and bank_obj.id or False
                line_vals['partner_id'] = partner_id
                line_vals['bank_account_id'] = bank_account_id
        return stmt_vals

    @api.multi
    def _parse_file(self, data_file):
        """Parse a CNAB file."""
        self.ensure_one()
        parser = cnabparser()
        try:
            _logger.debug("Try parsing with CNAB.")
            return parser.parse(data_file, self.import_modes)
        except ValueError:
            # Not a CNAB file, returning super will call next candidate:
            _logger.debug("Statement file was not a CNAB  file.",
                          exc_info=True)
            return super(AccountBankStatementImport, self)._parse_file(
                data_file)

    @api.model
    def _check_parsed_data(self, statements):
        """ Basic and structural verifications """
        if len(statements) == 0:
            raise Warning(_('This file doesn\'t contain any statement.'))
        for stmt_vals in statements:
            if 'transactions' in stmt_vals and stmt_vals['transactions']:
                return
        # Due to actual CNAB implementation, stmt_vals can have zero
        # transactions.
        # raise Warning(_('This file doesn\'t contain any transaction.'))

    @api.multi
    def write_data_on_move_line(self, data):
        self.ensure_one()

        move_line_name = data['ref']
        move_line_model = self.env['account.move.line']
        move_line_item = move_line_model.search(
            [('name', '=', move_line_name)], limit=1)
        move_line_item.transaction_ref = data['ref']
        move_line_item.ml_identificacao_titulo_no_banco = data[
            'identificacao_titulo_no_banco']

        cnab_move = self.env['l10n_br_cnab.move']
        cnab_move.create({
            'move_line_id': move_line_item.id,
            'str_ocorrencia': data['str_ocorrencia'],
            'str_motiv_a': data['str_motiv_a'],
            'str_motiv_b': data['str_motiv_b'],
            'str_motiv_c': data['str_motiv_c'],
            'str_motiv_d': data['str_motiv_d'],
            'str_motiv_e': data['str_motiv_e'],
            'data_ocorrencia': data['data_ocorrencia'],
        })

    @api.multi
    def write_data_on_paid_move_line(self, data):
        self.ensure_one()

        move_line_name = data['ref']
        move_line_model = self.env['account.move.line']
        move_line_item = move_line_model.search(
            [('name', '=', move_line_name)], limit=1)
        cnab_move = self.env['l10n_br_cnab.move']
        cnab_move.create({
            'move_line_id': move_line_item.id,
            'str_ocorrencia': data['str_ocorrencia'],
            'str_motiv_a': data['str_motiv_a'],
            'str_motiv_b': data['str_motiv_b'],
            'str_motiv_c': data['str_motiv_c'],
            'str_motiv_d': data['str_motiv_d'],
            'str_motiv_e': data['str_motiv_e'],
            'data_ocorrencia': data['data_ocorrencia'],
        })

    # Overrides temporarily
    @api.model
    def _import_file(self, data_file):
        """ Create bank statement(s) from file."""
        # The appropriate implementation module returns the required data
        statement_ids = []
        notifications = []
        parse_result = self._parse_file(data_file)
        # Check for old version result, with separate currency and account
        if isinstance(parse_result, tuple) and len(parse_result) == 3:
            (currency_code, account_number, statements) = parse_result
            for stmt_vals in statements:
                stmt_vals['currency_code'] = currency_code
                stmt_vals['account_number'] = account_number
        else:
            statements = parse_result
        # Check raw data:
        self._check_parsed_data(statements)
        # Import all statements:
        for stmt_vals in statements:
            (statement_id, new_notifications) = (
                self._import_statement(stmt_vals))
            if statement_id:
                statement_ids.append(statement_id)
            notifications.append(new_notifications)
        if len(statement_ids) == 0:
            pass
            # raise Warning(_('You have already imported that file.'))
        return statement_ids, notifications