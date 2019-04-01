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
        cnab_atual, cnab_atual_header = self._pega_cnab(record)

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
            cnab_passado, cnab_passado_header = self._pega_cnab(data)
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

        # DataFrame contendo eventos com valores diferentes
        df_eventos_diferentes = self._diferencas_cnab(
            cnab_atual=cnab_atual, cnab_passado=cnab_passado,
            dt_atual=dt_atual, dt_passada=dt_passada, index='favorecido_nome')

        # DataFrame contendo header com valores diferentes
        df_header_diferentes = self._diferencas_cnab(
            cnab_atual=cnab_atual_header, cnab_passado=cnab_passado_header,
            dt_atual=dt_atual, dt_passada=dt_passada, index='nome_do_banco')

        self.html_diferencas_cnabs = ''

        if len(df_header_diferentes):
            self.html_diferencas_cnabs += \
                '<h2><strong>Diferenças encontradas no cabeçalho do arquivo' \
                '</strong></h2> <br />'
            self.html_diferencas_cnabs += df_header_diferentes.to_html(
                classes=["oe_list_content", "table-bordered",
                         "table", "table-hover"])
            self.html_diferencas_cnabs += '<hr />'

        if len(novo_f):
            self.html_diferencas_cnabs += \
                '<h2><strong>Novos favorecidos:</strong></h2>'
            for novo in novo_f:
                self.html_diferencas_cnabs += '<p>{}</p>'.format(novo)
                self.html_diferencas_cnabs += '<hr />'

        if len(na_f):
            self.html_diferencas_cnabs += \
                '<h2><strong>Não são mais favorecidos:</strong></h2>'
            for na in na_f:
                self.html_diferencas_cnabs += '<p>{}</p>'.format(na)
                self.html_diferencas_cnabs += '<hr />'

        if len(df_eventos_diferentes):
            self.html_diferencas_cnabs += \
                '<h2><strong>Diferenças encontradas nos eventos</strong>' \
                '</h2> <br />'

            self.html_diferencas_cnabs += df_eventos_diferentes.to_html(
                classes=["oe_list_content", "table-bordered",
                         "table", "table-hover"])
            self.html_diferencas_cnabs += '<hr />'

        if self.html_diferencas_cnabs == '':
            self.html_diferencas_cnabs += \
                '<h2><strong>Nenhuma divergência encontrada</strong>' \
                '</h2> <br />'
            self.html_diferencas_cnabs += '<hr />'

    def _gera_df_cnab(self, cnab_obj):
        '''
        Cria um DataFrame a partir dos dados contidos no cnab

        :param cnab_obj: objeto do tipo Arquivo cnab
        :return: DataFrame
        '''
        # Cria lista com os campos do objeto
        data_eventos = \
            [{str(v): str(val._campos[v]).strip() for v in val._campos}
             for val in cnab_obj._lotes[0]._eventos]

        # Gera do DataFrame a partir da lista de eventos
        df_eventos = pd.DataFrame(data_eventos)

        # Define o nome do favorecido como index do DataFrame
        df_eventos.set_index('favorecido_nome', inplace=True)

        # Pega valores do header
        data_header = {str(val): str(cnab_obj.header._campos[val]).strip()
                       for val in cnab_obj.header._campos}

        # Gera do DataFrame a partir da lista de header
        df_header = pd.DataFrame(data_header, index=[0])

        # Define nome do banco como index
        df_header.set_index('nome_do_banco', inplace=True)

        return df_eventos, df_header

    def _pega_cnab(self, record):
        if record.cnab_file:
            cnab_obj = self.env['l10n.br.cnab'].read_cnab_file(
                record.cnab_file)
        else:
            raise UserError('CNAB do período passado não encontrado.')

        df_eventos, df_header = self._gera_df_cnab(cnab_obj=cnab_obj)

        return df_eventos, df_header

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

    def _diferencas_cnab(self, cnab_atual, cnab_passado, dt_atual, dt_passada,
                         index):
        '''
        Busca valores divergentes entre o cnab atual e o cnab passado(header e
        eventos).

        :param cnab_atual: DataFrame com eventos do cnab atual
        :param cnab_passado: DataFrame com eventos do cnab passado
        :param dt_atual: Data de pagamento do cnab atual
        :param dt_passada: Data de Pagamento do cnab passado
        :param index: Index da tabela

        :return: DataFrame contendo somente as diferenças encontradas
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
        df = df_a.merge(df_p, left_on=index, right_on=index,
                        suffixes=(' ({})'.format(dt_atual),
                                  ' ({})'.format(dt_passada)))

        df = df.replace(np.nan, '-', regex=True)

        return df
