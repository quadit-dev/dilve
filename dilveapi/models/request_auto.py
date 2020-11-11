# -*- coding: utf-8 -*-

from openerp import models, fields, api, tools, _
from openerp.exceptions import UserError, ValidationError, Warning
import requests
from xml.dom.minidom import parse, parseString
from xml.dom import minidom
from openerp.tools import ustr
from PIL import Image
from urllib import urlopen
from StringIO import StringIO
from datetime import datetime, timedelta
import base64
import validators
import logging

_logger = logging.getLogger(__name__)

class request_status(models.Model):
    _name = 'request.status'
    _inherit = ['mail.thread', 'ir.needaction_mixin']

    create_date = fields.Datetime('Fecha de solicitud', readonly=True)
    days = fields.Integer('Intervalo de días', required=True)
    requestType = fields.Selection([('A','Todos'),
                                    ('N','Nuevos'),
                                    ('C','Cambios'),
                                    ('D','Borrados')], 'Tipo', default="A", required=True)

    @api.model
    def request_dilve_auto(self):
        _logger.info('request_dilve_auto')
        if not self:
            self = self.search([])
        self.request_dilve()
        return True

    @api.multi
    def request_dilve(self):
        today = datetime.today()
        fdate = today-timedelta(days=self.days)
        formato = "%Y-%m-%d"
        from_date = datetime.strftime(fdate, formato)
        # _logger.info("===============>from_date %r" % from_date)
        publisher_id = self.env['codigos.editoriales'].search([('partner_id', '!=', False)])
        for publisher in publisher_id:
            _logger.info("=========================================================>publisher %r" % publisher.nombre)

            news_records = self.env['record.status'].get_status(from_date,'N',publisher.codigo)
            if news_records.status_code == 200:
                new_record = parseString(news_records.text)
                news_codes = new_record.getElementsByTagName("record")
                for new_code in news_codes:
                    codigoisbn = new_code.getElementsByTagName("id")[0]
                    code = str(codigoisbn.firstChild.data)
                    self.env['record.status'].get_record(code, publisher.codigo)

            changed_records = self.env['record.status'].get_status(from_date,'C',publisher.codigo)
            if changed_records.status_code == 200:
                changed_record = parseString(changed_records.text)
                changed_codes = changed_record.getElementsByTagName("record")
                for change_code in changed_codes:
                    codigoisbn = change_code.getElementsByTagName("id")[0]
                    code = str(codigoisbn.firstChild.data)
                    self.env['record.status'].get_record(code, publisher.codigo)

            deleted_records = self.env['record.status'].get_status(from_date,'D',publisher.codigo)
            if deleted_records.status_code == 200:
                deleted_record = parseString(deleted_records.text)
                deleted_codes = deleted_record.getElementsByTagName("record")
                for delete_code in deleted_codes:
                    codigoisbn = delete_code.getElementsByTagName("id")[0]
                    code = str(codigoisbn.firstChild.data)
                    self.env['deleted.records'].delete_record(code)
                    
        _logger.info("====================================================================>Finaliza DILVE")