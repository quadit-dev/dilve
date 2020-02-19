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
				res = self.dataRecord(code_br.isbn)
			
	@api.one
	def dataRecord(self,code):
		code = code
		datos = self.env['config.usuario']
		datos_id = datos.search([])
		urlRecords = "http://www.dilve.es/dilve/dilve/getRecordsX.do"
		dataRecords = requests.get(urlRecords, params = {"user":datos_id.user, 
			"password":datos_id.password, 
			"identifier":code})
		if dataRecords.status_code == 200:
			informacion = parseString(dataRecords.content)
			datos = informacion.getElementsByTagName("Product")
			for dato in datos:
				serie = dato.getElementsByTagName("Series")
				if serie:
					titulo = dato.getElementsByTagName("TitleText")[1]
				else:
					titulo = dato.getElementsByTagName("TitleText")[0]
				titulo = ustr(titulo.firstChild.data)
				contributor = dato.getElementsByTagName("PersonNameInverted")
				#for contrib in contributor:
				if contributor:
					autorD = dato.getElementsByTagName("PersonNameInverted")[0]
					autorD = ustr(autorD.firstChild.data)
				else:
					autorD = ""
				price = dato.getElementsByTagName("PriceAmount")
				if price:
					precio = dato.getElementsByTagName("PriceAmount")[0]
					precio = ustr(precio.firstChild.data)
				else:
					precio = 0
				priceSIVA = dato.getElementsByTagName("TaxableAmount1")
				if priceSIVA:
					precioSIVA = dato.getElementsByTagName("TaxableAmount1")[0]
					precioSIVA = ustr(precioSIVA.firstChild.data)
				else:
					precioSIVA = 0
				edit = dato.getElementsByTagName("ImprintName")
				if edit:
					editorialD = dato.getElementsByTagName("ImprintName")[0]
					editorialD = ustr(editorialD.firstChild.data)
				else:
					editorialD = ""
				page = dato.getElementsByTagName("NumberOfPages")
				if page:
					num_pag = dato.getElementsByTagName("NumberOfPages")[0]
					num_pag = ustr(num_pag.firstChild.data)
				else:
					num_pag = 0
				descrip = dato.getElementsByTagName("Text")
				if descrip:
					descripcion = dato.getElementsByTagName("Text")[0]
					descripcion = ustr(descripcion.firstChild.data)
				else:
					descripcion = ""
				images = dato.getElementsByTagName("MediaFileLink")
				i=0
				opcion=0
				for image in images:
					imagecode = dato.getElementsByTagName("MediaFileTypeCode")[i]
					imagecode = str(imagecode.firstChild.data)
					if imagecode=='04':
						url_image = dato.getElementsByTagName("MediaFileLink")[opcion]
						url_image = str(url_image.firstChild.data)
						if validators.url(url_image):
							img=True
							file = self.env['management.modifications'].cover_image(url_image)
							files = open('/tmp/imagen.jpg', 'r+')
							cover_image = files.read()
						else:
							img=False
							cover_image = None
						break
					else:
						img=False
						cover_image=None
						opcion=1
					i=i+1
				dispo = dato.getElementsByTagName("ProductAvailability")
				if dispo:
					disp = dato.getElementsByTagName("ProductAvailability")[0]
					disp = disp.firstChild.data
					estado = self.env['codigos.disponibilidad'].search([('codigo','=',disp)])
					disponibilidad = estado.vender
				else:
					disponibilidad = False
				pdate = dato.getElementsByTagName("PublicationDate")
				if pdate:
					public_date = dato.getElementsByTagName("PublicationDate")[0]
					public_date = public_date.firstChild.data
					public_date = public_date #+ ' 06:00:00'
                    _logger.info("===============>public_date %r" % public_date)
                    public_date = datetime.strptime(public_date, '%Y%m%d')
                    _logger.info("===============>public_date 2 %r" % public_date)
				else:
					public_date = False
				measures = dato.getElementsByTagName("MeasureTypeCode")
				m=0
				alto = ancho = grueso = peso = ""
				for measure in measures:
					measurecode = dato.getElementsByTagName("MeasureTypeCode")[m]
					if str(measurecode.firstChild.data)=='01':
						alto = dato.getElementsByTagName("Measurement")[m]
						alto = float(alto.firstChild.data)/10
					if str(measurecode.firstChild.data)=='02':
						ancho = dato.getElementsByTagName("Measurement")[m]
						ancho = float(ancho.firstChild.data)/10
					if str(measurecode.firstChild.data)=='03':
						grueso = dato.getElementsByTagName("Measurement")[m]
						grueso = float(grueso.firstChild.data)/10
					if str(measurecode.firstChild.data)=='08':
						peso = dato.getElementsByTagName("Measurement")[m]
						peso = float(peso.firstChild.data)
					m=m+1
				edicion = dato.getElementsByTagName("EditionNumber")
				if edicion:
					num_edicion = dato.getElementsByTagName("EditionNumber")[0]
					num_edicion = num_edicion.firstChild.data
				else:
					num_edicion = ""
				lugar = dato.getElementsByTagName("CountryOfPublication")
				if lugar:
					lugar_edicion = dato.getElementsByTagName("CountryOfPublication")[0]
					lugar_edicion = lugar_edicion.firstChild.data
				else:
					lugar_edicion = ""
			record = self.env['management.modifications'].search([('isbn','=',code)])
			registro = record.update({
				'isbn':code,
				'title':titulo,
				'price_amount':precio,
				'price_before_tax':precioSIVA,
				'autor':autorD,
				'editorial':editorialD,
				'page_num':num_pag,
				'other_text':descripcion,
				'url_image':img,
				'venta':disponibilidad,
				'compra':disponibilidad,
				'web':disponibilidad,
				#'publication_date':public_date,
				'height':alto,
				'width':ancho,
				'thick':grueso,
				'weight':peso,
				'edicion':num_edicion,
				'lugar_edicion':lugar_edicion
				})

			product = self.env['product.product'].search([('barcode','=',code)])
			product_dic = {
				'barcode':code,
				'name':titulo,
				'type':'product',
				'list_price':precioSIVA,
				'standard_price':precioSIVA,
				'sale_ok':disponibilidad,
				'purchase_ok':disponibilidad,
				'website_published':disponibilidad,
				###Estructura para los datos en el menu variants
				'fecha_publicacion_ok':public_date,
				'titulo_lang':titulo,
				'autor':autorD,
				'isbn_13':code,
				'editorial':editorialD,
				'numero_paginas':num_pag,
				'alto':alto,
				'ancho':ancho,
				'grueso':grueso,
				'peso':peso,
				'edicion':num_edicion,
				'texto_resumen':descripcion,
				'lugar_edicion':lugar_edicion
				}
			if cover_image:
				product_dic.update({
					'image_medium':base64.encodestring(cover_image)
				})
			producto = product.update(product_dic)

		return {
			'type': 'ir.actions.act_window',
            'res_model': 'ws.datos',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.id,
            'views': [(False, 'form')]
		}
