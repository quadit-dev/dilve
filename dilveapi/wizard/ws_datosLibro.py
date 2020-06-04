# -*- coding: utf-8 -*-

from openerp import models, fields, api, tools
import requests
from xml.dom.minidom import parse, parseString
from xml.dom import minidom
from openerp.tools import ustr
from PIL import Image
from urllib import urlopen
from StringIO import StringIO
from datetime import datetime
import base64
import validators
import logging

_logger = logging.getLogger(__name__)

class management_modifications(models.Model):
	_name = 'management.modifications'
	_inherit = 'management.modifications'

class ws_datos(models.Model):
	_name = 'ws.datos'
	_description = 'Datos de los libros'

	isbn = fields.Char('ISBN', size=13, readonly=True)
	title = fields.Char('Título', size=128, readonly=True)
	price_amount = fields.Float('Precio', readonly=True)
	price_before_tax = fields.Float('Precio(sin IVA)', readonly=True)
	autor = fields.Char('Autor', size=128, readonly=True)
	editorial = fields.Char('Editorial', size=128, readonly=True)
	page_num = fields.Integer('Número de páginas', size=128, readonly=True)
	other_text = fields.Char('Descripción', readonly=True)
	url_image = fields.Char('Imagen Cubierta', size=128, readonly=True)
	publication_date = fields.Datetime('Fecha de publicación', readonly=True)

	@api.model
	def default_get(self,values):
		res = super(ws_datos,self).default_get(values)
		active_id = self._context.get('active_ids')
		modifications_id = self.env['management.modifications'].browse(active_id)
		for modifications in modifications_id:
			res.update({
				'isbn':modifications.isbn,
				'title':modifications.title,
				'price_amount':modifications.price_amount,
				'price_before_tax':modifications.price_before_tax,
				'autor':modifications.autor,
				'editorial':modifications.editorial,
				'page_num':modifications.page_num,
				'other_text':modifications.other_text,
				'url_image':modifications.url_image
				})
		return res

	@api.multi
	def massiveData(self):
		active_ids = self._context['active_ids']
		for active_id in active_ids:
			code_br = self.env['management.modifications'].search([('id','=',active_id)])
			if code_br:
				res = self.env['record.status'].update_record(code_br.isbn)