from django.shortcuts import render
from django.http import HttpResponse
from django.views.decorators.http import require_GET
from prometheus_client.exposition import generate_latest
from prometheus_client import REGISTRY, CONTENT_TYPE_LATEST
from .custom_metrics import actualizar_metrica_usuarios, actualizar_metrica_websites

@require_GET
def metrics_view(request):
    # Actualizar métricas antes de generar el contenido
    actualizar_metrica_usuarios()
    actualizar_metrica_websites()

    # Devolver las métricas exportadas como respuesta HTTP
    output = generate_latest(REGISTRY)
    return HttpResponse(output, content_type=CONTENT_TYPE_LATEST)
