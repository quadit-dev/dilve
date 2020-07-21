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
from datetime import datetime
import base64
import validators
import logging

_logger = logging.getLogger(__name__)

class codigos_disponibilidad(models.Model):
    _name = 'codigos.disponibilidad'

    codigo = fields.Char('Código',size=02)
    descripcion = fields.Char('Descripción',size=128)
    vender = fields.Boolean('Puede ser vendido')
    comprar = fields.Boolean('Puede ser comprado')
    web = fields.Boolean('Publicar sitio web')

class codigos_editoriales(models.Model):
    _name = 'codigos.editoriales'
    _rec_name = 'nombre'

    nombre = fields.Char('Nombre', size=128)
    codigo = fields.Char('Código', size=12)
    partner_id = fields.Many2one('res.partner', 'Proveedor')
    category = fields.Many2one('product.category', 'Categoría interna')

class record_status(models.Model):
    _name = 'record.status'
    _inherit = ['mail.thread', 'ir.needaction_mixin']

    create_date = fields.Datetime('Fecha de solicitud', readonly=True)
    fromDate = fields.Datetime('Fecha de Inicio', required=True)
    toDate = fields.Datetime('Fecha de termino')
    requestType = fields.Selection([('A','Todos'),
                                    ('N','Nuevos'),
                                    ('C','Cambios'),
                                    ('D','Borrados')], 'Tipo', default="N")
    publisher = fields.Many2one(
        'codigos.editoriales', 
        'Editorial')
    country = fields.Char('País', size=128)

    @api.multi
    def getData(self):
        fDate = self.fromDate.split(' ')
        newFromDate = str(fDate[0]) + "T" + str(fDate[1]) + "Z"
        if self.toDate:
            tDate = self.toDate.split(' ')
            formato = "%Y-%m-%d"
            date = datetime.today()
            deadline = datetime.strptime(tDate[0], formato)
            diferencia = date - deadline
            if diferencia.days==0:
                raise Warning("[-] Seleccione una fecha de termino diferente")
            newToDate = str(tDate[0])
        else:
            newToDate = None
        if self.requestType:
            rType = str(self.requestType)
        else:
            rType = None
        if self.publisher:
            nPublisher = self.publisher.codigo
        else:
            nPublisher = None
        if self.country:
            nCountry = self.country
        else:
            nCountry = None
        recordList = self.get_status(newFromDate,rType,nPublisher,newToDate,nCountry)

        if recordList.status_code == 200:
            codigos = parseString(recordList.text)
            libros = codigos.getElementsByTagName("record")
            for libro in libros:
                codigoisbn = libro.getElementsByTagName("id")[0]
                code = str(codigoisbn.firstChild.data)
                if self.requestType=='D':
                    self.env['deleted.records'].delete_record(code)
                else:
                    record = self.env['product.template'].search([('barcode','=',code)])
                    res = self.get_record(code, nPublisher)

    @api.multi
    def get_status(self,from_date,rtype,publisher,to_date=None,country=None):
        datos = self.env['config.usuario']
        datos_id = datos.search([])
        url = "http://www.dilve.es/dilve/dilve/getRecordStatusX.do"
        paramsapi = {"user":datos_id.user, 
            "password":datos_id.password, 
            "fromDate":from_date,
            "toDate":to_date,
            "type":rtype,
            "publisher":publisher,
            "country":country
            }
        res = requests.get(url, params=paramsapi)
        return res

    @api.multi
    def get_record(self, code, publisher=None):
        titulo = precioSIVA = precioSIVA = precio = public_date = disp_venta = disp_compra = disp_web = descripcion = cover_image = False
        autorD = editorialD = num_pag = alto = ancho = grueso = num_edicion = lugar_edicion = img = False
        code = code
        datos = self.env['config.usuario']
        datos_id = datos.search([])
        urlRecords = "http://www.dilve.es/dilve/dilve/getRecordsX.do"
        dataRecords = requests.get(urlRecords, 
            params = {"user":datos_id.user, 
            "password":datos_id.password, 
            "identifier":code})
        if dataRecords.status_code == 200:
            informacion = parseString(dataRecords.content)
            datos = informacion.getElementsByTagName("Product")
            for dato in datos:
                producto = dato.getElementsByTagName("ProductForm")[0]
                producto = producto.firstChild.data
                if producto[0] == "B":
                    serie = dato.getElementsByTagName("Series")
                    if serie:
                        titles = dato.getElementsByTagName("TitleType")
                        titletype = len([title.firstChild.data for title in titles if title.firstChild.data == '01'])
                        titulo = dato.getElementsByTagName("TitleText")[titletype-1]
                    else:
                        titulo = dato.getElementsByTagName("TitleText")[0]
                    titulo = ustr(titulo.firstChild.data)
                    contributor = dato.getElementsByTagName("PersonNameInverted")
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
                    
                    edit = dato.getElementsByTagName("Publisher")
                    if edit:
                        editorialD = dato.getElementsByTagName("PublisherName")[0]
                        editorialD = ustr(editorialD.firstChild.data)
                        code_editorial = dato.getElementsByTagName("NameCodeValue")[0]
                        code_editorial = ustr(code_editorial.firstChild.data)
                    else:
                        editorialD = ""
                        code_editorial = ""
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
                    img=False
                    cover_image=None
                    for image in images:
                        imagecode = dato.getElementsByTagName("MediaFileTypeCode")[i]
                        imagecode = str(imagecode.firstChild.data)
                        if imagecode=='04':
                            url_image = dato.getElementsByTagName("MediaFileLink")[opcion]
                            url_image = str(url_image.firstChild.data)
                            if validators.url(url_image):
                                img = self.cover_image(url_image,code)
                                if img==True:
                                    files = open('/tmp/imagen.jpg', 'r+')
                                    cover_image = files.read()
                            else:
                                url_resource = "http://www.dilve.es/dilve/dilve/getResourceX.do?user="+ datos_id.user + "&password=" + datos_id.password + "&identifier=" + code + "&resource=" + url_image
                                img = self.cover_image(url_resource,code)
                                if img==True:
                                    files = open('/tmp/imagen.jpg', 'r+')
                                    cover_image = files.read()
                            break
                        else:
                            img=False
                            cover_image=None
                            opcion=1
                        i=i+1
                    pdate = dato.getElementsByTagName("PublicationDate")
                    if pdate:
                        public_date = dato.getElementsByTagName("PublicationDate")[0]
                        public_date = public_date.firstChild.data
                        public_date = public_date #+ ' 06:00:00'
                        public_date = datetime.strptime(public_date, '%Y%m%d')
                    else:
                        public_date = False
                    dispo = dato.getElementsByTagName("ProductAvailability")
                    if dispo:
                        disp = dato.getElementsByTagName("ProductAvailability")[0]
                        disp = disp.firstChild.data
                        estado = self.env['codigos.disponibilidad'].search([('codigo','=',disp)])
                        disp_venta = estado.vender
                        disp_compra = estado.comprar
                        disp_web = estado.web
                    else:
                        disp_venta = disp_compra = disp_web = False
                    measures = dato.getElementsByTagName("MeasureTypeCode")
                    m=0
                    alto = ancho = grueso = peso = "0.0"
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
                            peso = peso / 1000
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
            if titulo:
                record = self.env['management.modifications'].search([('isbn','=',code)])
                if record:
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
                        'venta':disp_venta,
                        'compra':disp_compra,
                        'web':disp_web,
                        'height':alto,
                        'width':ancho,
                        'thick':grueso,
                        'weight':peso,
                        'edicion':num_edicion,
                        'lugar_edicion':lugar_edicion
                        })
                else:
                    registro = record.create({
                        'isbn':code,
                        'title':titulo,
                        'price_amount':precio,
                        'price_before_tax':precioSIVA,
                        'autor':autorD,
                        'editorial':editorialD,
                        'page_num':num_pag,
                        'other_text':descripcion,
                        'url_image':img,
                        'venta':disp_venta,
                        'compra':disp_compra,
                        'web':disp_web,
                        'publication_date':public_date,
                        'height':alto,
                        'width':ancho,
                        'thick':grueso,
                        'weight':peso,
                        'edicion':num_edicion,
                        'lugar_edicion':lugar_edicion
                        })

                product = self.env['product.product'].search([('barcode','=',code)])
                # _logger.info("===============>product %r" % product)
                product_dic = {
                    'barcode':code,
                    'name':titulo,
                    'type':'product',
                    'list_price':precioSIVA,
                    'standard_price':precioSIVA,
                    'sale_ok':disp_venta,
                    'purchase_ok':disp_compra,
                    'website_published':disp_web,
                    'weight':peso,
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

                if not publisher:
                    publisher = code_editorial

                prov = self.env['codigos.editoriales'].search([('codigo', '=', publisher)])
                if prov.category:
                    product_dic.update({
                        'categ_id':int(prov.category)
                    })

                if product:
                    producto = product.update(product_dic)
                    produ = product
                else:
                    producto = product.create(product_dic)
                    produ = producto

                try:
                    if cover_image:
                        producto = product.update({'image_medium':base64.encodestring(cover_image)})
                except Exception:
                    return False

                rules = self.env['stock.warehouse.orderpoint']
                if not rules.search([('product_id', '=', produ.id)]):
                    rule = {
                        'name':'OP/00110',
                        'product_id':int(produ.id),
                        'product_min_qty':'0',
                        'product_max_qty':'0',
                        'qty_multiple':'1',
                        'warehouse_id':'1',
                        'location_id':'12',
                        'active':True,
                        'lead_days':'1',
                        'lead_type':'supplier'
                    }
                    orderpoint = rules.create(rule)

                supplier = self.env['product.supplierinfo']
                if not supplier.search([('product_id', '=', produ.id)]):
                    if prov.partner_id:
                        product_template = self.env['product.template'].search([('barcode','=',code)])
                        seller = {
                            'product_tmpl_id': int(product_template),
                            'product_id': int(produ.id),
                            'name': int(prov.partner_id),
                            'product_uom': 1,
                            'sequence': 1,
                            'company_id': 1,
                            'qty': float('0.0'),
                            'delay': 1,
                            'min_qty': 0,
                            'price': precioSIVA
                        }
                        proveedor = supplier.create(seller)
            else:
                product = self.env['product.template'].search([('barcode','=',code)])
                if product:
                    product_dic = {
                        'barcode':code,
                        'sale_ok':disp_venta,
                        'purchase_ok':disp_compra,
                        'website_published':disp_web
                    }
                    producto = product.update(product_dic)

    @api.multi
    def cover_image(self, url, code):
        try:
            #_logger.info("===============>url %r" % url)
            data = requests.get(url)
            with open("/tmp/imagen.jpg", "wb") as codes:
                codes.write(data.content)
            return True
        except Exception:
            post_vars = {'subject': 'Mensaje', 'body': _('El siguiente código presento error, reviselo manualmente. %r' % str(code)), }
            self.message_post(type="notification", subtype="mt_comment", **post_vars)
            return False

class management_modifications(models.Model):
    _name = 'management.modifications'
    _description = 'Modelo de las modificaciones existentes en un intervalo de fechas.'

    create_date = fields.Datetime('Fecha de creación', readonly=True)
    isbn = fields.Char('ISBN', size=13, readonly=True)
    title = fields.Char('Título', size=128, readonly=True)
    price_amount = fields.Float('Precio', readonly=True)
    price_before_tax = fields.Float('Precio(sin IVA)', readonly=True)
    autor = fields.Char('Autor', size=128, readonly=True)
    editorial = fields.Char('Editorial', size=128, readonly=True)
    page_num = fields.Integer('Número de páginas', size=128, readonly=True)
    other_text = fields.Char('Descripción', readonly=True)
    url_image = fields.Boolean('Imagen Cubierta',readonly=True)
    publication_date = fields.Datetime('Fecha de publicación', readonly=True)
    height = fields.Float('Altura', readonly=True)
    width = fields.Float('Ancho', readonly=True)
    thick = fields.Float('Grueso', readonly=True)
    weight = fields.Float('Peso', readonly=True)
    edicion = fields.Char('Número de edición', readonly=True)
    lugar_edicion = fields.Char('Lugar de edición', readonly=True)

    venta = fields.Boolean('Puede ser vendido')
    compra = fields.Boolean('Puede ser comprado')
    web = fields.Boolean('Publicar sitio web')