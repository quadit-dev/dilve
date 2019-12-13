# -*- coding: utf-8 -*-
from openerp import http

# class Dilveapi(http.Controller):
#     @http.route('/dilveapi/dilveapi/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/dilveapi/dilveapi/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('dilveapi.listing', {
#             'root': '/dilveapi/dilveapi',
#             'objects': http.request.env['dilveapi.dilveapi'].search([]),
#         })

#     @http.route('/dilveapi/dilveapi/objects/<model("dilveapi.dilveapi"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('dilveapi.object', {
#             'object': obj
#         })