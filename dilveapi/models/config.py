# -*- coding: utf-8 -*-

from openerp import models, fields, api, tools
import requests

class config_usuario(models.Model):
	_name = 'config.usuario'
	_description = 'Modelo para la configuracion del usuario de Dilve'

	user = fields.Char('Usuario', size=128, required=True)
	password = fields.Char('Contraseña', size=128, required=True)
