# -*- coding: utf-8 -*-

from openerp import models, fields, api, tools
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

class record_status(models.Model):
    _name = 'record.status'

    create_date = fields.Datetime('Fecha de solicitud', readonly=True)
    fromDate = fields.Datetime('Fecha de Inicio', required=True)
    toDate = fields.Datetime('Fecha de termino')
    requestType = fields.Selection([#('A','Todos'),
                                    ('N','Nuevos'),
                                    ('C','Cambios'),
                                    ('D','Borrados')], 'Tipo', default="N")
    detail = fields.Selection([('N','Normal'),
                                    ('D','Fecha')], 'Detalle', default="N")
    hyphens = fields.Selection([('N','No'),
                                    ('Y','Si')], 'Guiones', default="N")
    publisher = fields.Many2one(
        'codigos.editoriales', 
        'Editorial')
    publishertype = fields.Selection([('A','Autor/Editor'),
                                    ('E','Editorial'),
                                    ('ED','Editoriales DILVE'),
                                    ('EP','Editoriales Plataforma ISBN')], 
                                    'Tipo de editorial', default="E")
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
        if self.detail:
            nDetail = str(self.detail)
        else:
            nDetail = None
        if self.hyphens:
            nHyphens = str(self.hyphens)
        else:
            nHyphens = None
        if self.publisher:
            nPublisher = self.publisher.codigo
        else:
            nPublisher = None
        if self.publishertype:
            nPublishertype = str(self.publishertype)
        else:
            nPublishertype = None
        if self.country:
            nCountry = self.country
        else:
            nCountry = None
        datos = self.env['config.usuario']
        datos_id = datos.search([])
        url = "http://www.dilve.es/dilve/dilve/getRecordStatusX.do"
        paramsapi = {"user":datos_id.user, 
            "password":datos_id.password, 
            "fromDate":newFromDate,
            "toDate":newToDate,
            "type":rType,
            "detail":nDetail,
            "hyphens":nHyphens,
            "publisher":nPublisher,
            "publishertype":nPublishertype,
            "country":nCountry
            }
        recordList = requests.get(url, params=paramsapi)

        if recordList.status_code == 200:
            codigos = parseString(recordList.text)
            libros = codigos.getElementsByTagName("record")
            for libro in libros:
                codigoisbn = libro.getElementsByTagName("id")[0]
                code = str(codigoisbn.firstChild.data)
                if self.requestType=='D':
                    products = self.env['product.template'].search([('barcode','=',code)])
                    if products:
                        registro = self.env['deleted.records'].create({
                            'isbn':code,
                            'title':products.name
                            })
                else:
                    record = self.env['product.template'].search([('barcode','=',code)])
                    if record:
                        res = self.update_record(code)
                    else:
                        datos = self.env['config.usuario']
                        datos_id = datos.search([])
                        paramsapirecords = {"user":datos_id.user, 
                            "password":datos_id.password,
                            "identifier":code}
                        urlRecords = "http://www.dilve.es/dilve/dilve/getRecordsX.do"
                        dataRecords = requests.get(urlRecords, params = paramsapirecords)
                        if dataRecords.status_code == 200:
                            informacion = parseString(dataRecords.content)
                            datos = informacion.getElementsByTagName("Product")
                            for dato in datos:
                                serie = dato.getElementsByTagName("Series")
                                if serie:
                                    titulo = dato.getElementsByTagName("TitleText")[1]
                                else:
                                    titulo = dato.getElementsByTagName("TitleText")[0]
                                titulo = titulo.firstChild.data
                                contributor = dato.getElementsByTagName("PersonNameInverted")
                                #for contrib in contributor:
                                if contributor:
                                    autorD = dato.getElementsByTagName("PersonNameInverted")[0]
                                    autorD = autorD.firstChild.data
                                else:
                                    autorD = ""
                                price = dato.getElementsByTagName("PriceAmount")
                                if price:
                                    precio = dato.getElementsByTagName("PriceAmount")[0]
                                    precio = precio.firstChild.data
                                else:
                                    precio = 0
                                priceSIVA = dato.getElementsByTagName("TaxableAmount1")
                                if priceSIVA:
                                    precioSIVA = dato.getElementsByTagName("TaxableAmount1")[0]
                                    precioSIVA = precioSIVA.firstChild.data
                                else:
                                    precioSIVA = 0
                                edit = dato.getElementsByTagName("ImprintName")
                                if edit:
                                    editorialD = dato.getElementsByTagName("ImprintName")[0]
                                    editorialD = editorialD.firstChild.data
                                else:
                                    editorialD = ""
                                page = dato.getElementsByTagName("NumberOfPages")
                                if page:
                                    num_pag = dato.getElementsByTagName("NumberOfPages")[0]
                                    num_pag = num_pag.firstChild.data
                                else:
                                    num_pag = 0
                                descrip = dato.getElementsByTagName("Text")
                                if descrip:
                                    descripcion = dato.getElementsByTagName("Text")[0]
                                    descripcion = descripcion.firstChild.data
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
                                            img = True
                                            file = self.env['management.modifications'].cover_image(url_image)
                                            files = open('/tmp/imagen.jpg', 'r+')
                                            cover_image = files.read()
                                        else:
                                            img=False
                                            cover_image = None
                                        break
                                    else:
                                        img=False
                                        cover_image = None
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
                                    public_date = public_date + ' 06:00:00'
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
                        if not record:
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
                                'venta':disponibilidad,
                                'compra':disponibilidad,
                                'web':disponibilidad,
                                'publication_date':public_date,
                                'height':alto,
                                'width':ancho,
                                'thick':grueso,
                                'weight':peso,
                                'edicion':num_edicion,
                                'lugar_edicion':lugar_edicion
                                })
                        product = self.env['product.product']
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
                        producto = product.create(product_dic)

                        supplier = self.env['product.supplierinfo']
                        seller = {
                            'product_tmpl_id': int(producto),
                            'name': int(self.publisher.partner_id),
                            'delay': 1,
                            'min_qty': 0.00,
                            'price': precioSIVA
                        }
                        proveedor = supplier.create(seller)


        return {
            'type': 'ir.actions.act_window',
            'res_model': 'record.status',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.id,
            'views': [(False, 'form')]
        }

    @api.multi
    def update_record(self,code):
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
                serie = dato.getElementsByTagName("Series")
                if serie:
                    titulo = dato.getElementsByTagName("TitleText")[1]
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
                img=False
                cover_image=None
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
                pdate = dato.getElementsByTagName("PublicationDate")
                if pdate:
                    public_date = dato.getElementsByTagName("PublicationDate")[0]
                    public_date = public_date.firstChild.data
                    #public_date = datetime.strptime(public_date, '%Y%m%d')
                    public_date = public_date + ' 06:00:00'
                else:
                    public_date = False
                dispo = dato.getElementsByTagName("ProductAvailability")
                if dispo:
                    disp = dato.getElementsByTagName("ProductAvailability")[0]
                    disp = disp.firstChild.data
                    estado = self.env['codigos.disponibilidad'].search([('codigo','=',disp)])
                    disponibilidad = estado.vender
                else:
                    disponibilidad = False
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
                    'venta':disponibilidad,
                    'compra':disponibilidad,
                    'web':disponibilidad,
                    'publication_date':public_date,
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

class management_modifications(models.Model):
    _name = 'management.modifications'
    _description = 'Modelo de las modificaciones existentes en un intervalo de fechas.'

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

    @api.multi
    def cover_image(self, url):
        url = url
        data = urlopen(url).read()
        file = StringIO(data)
        image = Image.open(file)
        image.save('/tmp/imagen.jpg')

class deleted_records(models.Model):
    _name = 'deleted.records'
    _description = 'Modelo para manejar las bajas de los libros.'

    isbn = fields.Char('ISBN', size=13, readonly=True)
    title = fields.Char('Título', size=128, readonly=True)
    autor = fields.Char('Autor', size=128, readonly=True)
    editorial = fields.Char('Editorial', size=128, readonly=True)
