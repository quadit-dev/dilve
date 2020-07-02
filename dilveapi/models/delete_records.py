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
import logging

_logger = logging.getLogger(__name__)

class deleted_records(models.Model):
    _name = 'deleted.records'
    _description = 'Modelo para manejar las bajas de los libros.'

    isbn = fields.Char('ISBN', size=13, readonly=True)
    title = fields.Char('Título', size=128, readonly=True)
    autor = fields.Char('Autor', size=128, readonly=True)
    editorial = fields.Char('Editorial', size=128, readonly=True)

    @api.multi
    def delete_record(self, code):
        disponibilidad = False
        products = self.env['product.product'].search([('barcode','=',code)])
        if products:
            _logger.info("===============>code %r" % code)
            registro = self.env['deleted.records'].create({
                'isbn':code,
                'title':products.name,
                'autor':products.autor,
                'editorial':products.editorial
            })
            product = self.env['product.product'].search([('barcode','=',code)])
            product_dic = {
                'sale_ok':disponibilidad,
                'purchase_ok':disponibilidad,
                'website_published':disponibilidad
            }
            producto = product.update(product_dic)