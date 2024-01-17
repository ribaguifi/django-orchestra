from prometheus_client import start_http_server, Gauge
import random

from orchestra.contrib.accounts.models import Account
from orchestra.contrib.websites.models import Website


# Crear métricas de tipo Gauge con etiquetas
usuarios_metrica = Gauge('usuarios', 'Número total de usuarios', ['estado'])
websites_metrica = Gauge('websites_server', 'Número total de websites en server', ['target_server', 'estado'])

def actualizar_metrica_usuarios():
    # Generar una lista de usuarios aleatorios para el ejemplo
    usuarios = Account.objects.all()

    # Contar usuarios activos, no activos y actualizar la métrica
    usuarios_activos = sum(1 for usuario in usuarios if usuario.is_active)
    usuarios_no_activos = len(usuarios) - usuarios_activos

    usuarios_metrica.labels(estado='activo').set(usuarios_activos)
    usuarios_metrica.labels(estado='no_activo').set(usuarios_no_activos)
    usuarios_metrica.labels(estado='total').set(len(usuarios))


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

        