# -*- coding: utf-8 -*-

from openerp import models, fields, api, tools
import requests
from xml.dom.minidom import parse, parseString
from xml.dom import minidom
from openerp.tools import ustr
from PIL import Image
from urllib import urlopen
from StringIO import StringIO
import datetime
import base64
import validators

class product_template(models.Model):
	_name = 'product.template'
	_inherit = 'product.template'

class ws_records(models.Model):
	_name = 'ws.records'
	_description = 'Datos de los libros en inventario.'

	barcode = fields.Char('ISBN', size=13, readonly=True)
	name = fields.Char('Título', size=128, readonly=True)
	list_price = fields.Float('Precio', readonly=True)
	standard_price = fields.Float('Precio(sin IVA)', readonly=True)
	
	sale_ok = fields.Boolean('Puede ser vendido')
	purchase_ok = fields.Boolean('Puede ser comprado')
	website_published = fields.Boolean('Publicar sitio web')

	@api.model
	def default_get(self,values):
		res = super(ws_records,self).default_get(values)
		active_id = self._context.get('active_ids')
		records_id = self.env['product.template'].browse(active_id)
		for records in records_id:
			res.update({
				'barcode':records.barcode,
				'name':records.name,
				'list_price':records.list_price,
				'standard_price':records.standard_price,
				'sale_ok':records.sale_ok,
				'purchase_ok':records.purchase_ok,
				'website_published':records.website_published
				})
		return res

	@api.multi
	def massiveRecord(self):
		active_ids = self._context['active_ids']
		for active_id in active_ids:
			code_br = self.env['product.template'].search([('id','=',active_id)])
			if code_br:
				res = self.env['record.status'].update_record(code_br.barcode)