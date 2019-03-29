# -*- coding: utf-8 -*-
# Copyright 2017 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import pandas as pd
import numpy as np
import datetime
from openerp import api, models, fields, _
from openerp.exceptions import Warning as UserError


class PaymentOrderValidaCnabWizard(models.TransientModel):
    _name = "payment.order.validacnab.wizard"

    html_diferencas_cnabs = fields.Html(
        string='Diferenças encontradas',
    )

    @api.multi
    def validar_cnab(self, payment_order_id):
        self.ensure_one()

        payment_order = self.env['payment.order']
        record = payment_order.browse(payment_order_id)

        # DataFrame com o cnab atual
        cnab_atual = self._pega_cnab(record)

        # pega ano-mês anterior
        periodo_atual = datetime.datetime.strptime(
            record.date_scheduled, '%Y-%m-%d').date()
        primeiro_dia = periodo_atual.replace(day=1)
        ultimo_mes = primeiro_dia - datetime.timedelta(days=1)
        mes_passado = ultimo_mes.strftime("%Y-%m")

        data = payment_order.search(
            [('mode.id', '=', record.mode.id),
             ('date_scheduled', 'ilike', mes_passado),
             ('tipo_de_folha', '=', record.tipo_de_folha)])

        if len(data):
            # DataFrame com o cnab passado
            cnab_passado = self._pega_cnab(data)
        else:
            raise UserError('Periodo passa não encontrado.')

        # Busca novos favorecidos e antigos que não constam mais e limpa
        # DataFrames
        cnab_atual, cnab_passado, novo_f, na_f = \
            self._diferencas_cnab_index(
                cnab_atual=cnab_atual, cnab_passado=cnab_passado)

        dt_atual = datetime.datetime.strptime(
            record.date_scheduled, '%Y-%m-%d').strftime('%d/%m/%Y')
        dt_passada = datetime.datetime.strptime(
            data.date_scheduled, '%Y-%m-%d').strftime('%d/%m/%Y')

        df = self._diferencas_cnab(
            cnab_atual=cnab_atual,
            cnab_passado=cnab_passado,
            dt_atual=dt_atual,
            dt_passada=dt_passada)

        self.html_diferencas_cnabs = ''
        if len(novo_f):
            self.html_diferencas_cnabs += \
                '<p><strong>Novos favorecidos:</strong></p>'
            for novo in novo_f:
                self.html_diferencas_cnabs += '<p>{}</p>'.format(novo)

        if len(na_f):
            self.html_diferencas_cnabs += \
                '<p><strong>Não são mais favorecidos:</strong></p>'
            for na in na_f:
                self.html_diferencas_cnabs += '<p>{}</p>'.format(na)

        if len(df):
            self.html_diferencas_cnabs += \
                '<p><strong>Diferenças encontradas</strong></p>'

            self.html_diferencas_cnabs += df.to_html(
                classes=["oe_list_content", "table-bordered",
                         "table", "table-hover"])

        if self.html_diferencas_cnabs == '':
            self.html_diferencas_cnabs += \
                '<p><strong>Nenhuma divergência encontrada</strong></p>'

        return cnab_passado, cnab_atual

    def _gera_df_cnab(self, cnab_obj):
        '''
        Cria um DataFrame a partir dos dados contidos no cnab

        :param cnab_obj: objeto do tipo Arquivo cnab
        :return: DataFrame
        '''
        # Cria lista com os campos do objeto
        data = [{str(v): str(val._campos[v]).strip() for v in val._campos}
                for val in cnab_obj._lotes[0]._eventos]

        # Gera do DataFrame a partir da lista
        df = pd.DataFrame(data)

        # Define o nome do favorecido como index do DataFrame
        df.set_index('favorecido_nome', inplace=True)

        return df

    def _pega_cnab(self, record):
        if record.cnab_file:
            cnab_obj = self.env['l10n.br.cnab'].read_cnab_file(
                record.cnab_file)
        else:
            raise UserError('CNAB do período passado não encontrado.')

        return self._gera_df_cnab(cnab_obj=cnab_obj)

    def _diferencas_cnab_index(self, cnab_atual, cnab_passado):
        '''
        Busca favorecidos que existe em uma lista e não existe na outra e
        limpa as listas

        :param cnab_atual: cnab atual
        :param cnab_passado: cnab passado
        :return: novos favorecidos e favorecidos que não constam mais
        '''
        # Busca por novos favorecidos
        novo_f = cnab_atual[
            cnab_atual.index.isin(cnab_passado.index) == False].index

        # Busca por favorecidos que não constam mais
        na_f = cnab_passado[
            cnab_passado.index.isin(cnab_atual.index) == False].index

        # ordena cnabs
        cnab_atual.sort_index(inplace=True)
        cnab_passado.sort_index(inplace=True)

        # apaga novos favorecidos da lista atual
        for novo in novo_f:
            cnab_atual.drop(novo, inplace=True)

        # apaga favorecidos antigos que não constam da lista passada
        for na in na_f:
            cnab_passado.drop(na, inplace=True)

        # Remove colunas que serão sempre diferentes
        cnab_atual.drop(inplace=True,
            columns=['credito_data_pagamento', 'servico_numero_registro',
                     'credito_seu_numero'])

        cnab_passado.drop(inplace=True,
            columns=['credito_data_pagamento', 'servico_numero_registro',
                     'credito_seu_numero'])

        return cnab_atual, cnab_passado, novo_f, na_f

    def _diferencas_cnab(self, cnab_atual, cnab_passado, dt_atual, dt_passada):
        '''
        Busca valores divergentes entre o cnab atual e o cnab passado

        :param cnab_atual:
        :param cnab_passado:
        :return: DataFrame com diferenças
        '''
        # Busca valores diferentes da atual na passada
        df_a = cnab_atual[cnab_atual[cnab_atual != cnab_passado].notnull()]
        null_cols_a = df_a.columns[df_a.isnull().all()]
        df_a.drop(null_cols_a, axis=1, inplace=True)

        # Busca valores diferente da passada na atual
        df_p = cnab_passado[cnab_passado[cnab_passado != cnab_atual].notnull()]
        null_cols_p = df_p.columns[df_p.isnull().all()]
        df_p.drop(null_cols_p, axis=1, inplace=True)

        # Une os resultados em um dataframe
        df = df_a.merge(df_p, left_on='favorecido_nome',
                        right_on='favorecido_nome',
                        suffixes=(' ({})'.format(dt_atual),
                                  ' ({})'.format(dt_passada)))
        df = df.replace(np.nan, '-', regex=True)

        return df
