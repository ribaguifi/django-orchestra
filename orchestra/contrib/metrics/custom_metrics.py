from prometheus_client import start_http_server, Gauge
import random

from orchestra.contrib.accounts.models import Account
from orchestra.contrib.websites.models import Website
from orchestra.contrib.databases.models import Database
from orchestra.contrib.resources.models import ResourceData
from orchestra.contrib.mailboxes.models import Mailbox
from orchestra.contrib.lists.models import List
from orchestra.contrib.saas.models import SaaS


# Crear métricas de tipo Gauge con etiquetas
usuarios_metrica = Gauge('usuarios', 'Número total de usuarios', ['tipo', 'estado'])
usuarios_top_size_metrica = Gauge('usuarios_top_size', 'Top 10 cuentas ocupan espacio', ['account'])
websites_metrica = Gauge('websites_server', 'Número total de websites en server', ['target_server', 'estado'])
databases_metrica = Gauge('databases', 'Número total de websites en server', ['target_server'])
databases_top_size_metrica = Gauge('databases_top_size', 'Top 10 databases ocupan espacio', ['database'])
mailboxes_metrica = Gauge('mailbox', 'Número total de mailbox', ['estado'])
mailboxes_top_size_metrica = Gauge('mailboxes_top_size', 'Top 10 mailboxes ocupan espacio', ['mailbox'])
lists_metrica = Gauge('lists', 'Número total de listas')
saas_metrica = Gauge('saas', 'Número total de saas', ['service', 'estado'])
saas_top_size_metrica = Gauge('saas_top_size', 'Top 10 saas ocupan espacio', ['saas'])

def actualizar_metrica_usuarios():
    # Generar una lista de usuarios aleatorios para el ejemplo
    usuarios = Account.objects.all()
    
    user_dict = {}
    for user in usuarios:
        if user.type not in user_dict.keys():
            user_dict[user.type] = {'activo':0, 'inactivo':0} 
        
        if user.is_active:
            user_dict[user.type]['activo'] += 1
        else:
            user_dict[user.type]['inactivo'] += 1

    # envia metrica por cada tipo de usuario num de activos y inactivos
    for type, value in user_dict.items():
        usuarios_metrica.labels(tipo=type, estado='activo').set(value['activo'])
        usuarios_metrica.labels(tipo=type, estado='no_activo').set(value['inactivo'])

    top_resources = ResourceData.objects.filter(resource_id=4, used__isnull=False).order_by('-used')[:10]
    for resourcedata in top_resources:
        usuarios_top_size_metrica.labels(account=resourcedata.content_object_repr).set(resourcedata.used)


def actualizar_metrica_websites():
    websites = Website.objects.all()

    website_dict = {}
    for website in websites:
        if website.target_server.name not in website_dict.keys():
            website_dict[website.target_server.name] = {'activo':0, 'inactivo':0} 
        
        if website.is_active:
            website_dict[website.target_server.name]['activo'] += 1
        else:
            website_dict[website.target_server.name]['inactivo'] += 1

    for server, value in website_dict.items():
        websites_metrica.labels(target_server=server, estado='activo').set(value['activo'])
        websites_metrica.labels(target_server=server, estado='no_activo').set(value['inactivo'])


def actualizar_metrica_databases():
    databases = Database.objects.all()

    data = {}
    for database in databases:
        if database.target_server.name not in data.keys():
            data[database.target_server.name] = {'total':0}         
        data[database.target_server.name]['total'] += 1
        
    for server, value in data.items():
        databases_metrica.labels(target_server=server).set(value['total'])

    top_resources = ResourceData.objects.filter(resource_id=5, used__isnull=False).order_by('-used')[:10]
    for resourcedata in top_resources:
        databases_top_size_metrica.labels(database=resourcedata.content_object_repr).set(resourcedata.used)


def actualizar_metrica_mailboxes():
    mailboxes = Mailbox.objects.all()
    
    mailbox_activos = sum(1 for mailbox in mailboxes if mailbox.is_active)
    mailbox_inactivos = len(mailboxes) - mailbox_activos

    mailboxes_metrica.labels(estado='activo').set(mailbox_activos)
    mailboxes_metrica.labels(estado='no_activo').set(mailbox_inactivos)

    top_resources = ResourceData.objects.filter(resource_id=1, used__isnull=False).order_by('-used')[:10]
    for resourcedata in top_resources:
        mailboxes_top_size_metrica.labels(mailbox=resourcedata.content_object_repr).set(resourcedata.used)


def actualizar_metrica_lists():
    lists = List.objects.all()
    lists_metrica.set(len(lists))

def actualizar_metrica_saas():
    saases = SaaS.objects.all()

    saas_dict = {}
    for saas in saases:
        if saas.service not in saas_dict.keys():
            saas_dict[saas.service] = {'activo':0, 'inactivo':0} 
        
        if saas.is_active:
            saas_dict[saas.service]['activo'] += 1
        else:
            saas_dict[saas.service]['inactivo'] += 1

    for servicio, value in saas_dict.items():
        saas_metrica.labels(service=servicio, estado='activo').set(value['activo'])
        saas_metrica.labels(service=servicio, estado='no_activo').set(value['inactivo'])

    top_resources = ResourceData.objects.filter(resource_id=23, used__isnull=False).order_by('-used')[:10]
    for resourcedata in top_resources:
        saas_top_size_metrica.labels(saas=resourcedata.content_object_repr).set(resourcedata.used)