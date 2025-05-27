import os
import textwrap

from orchestra.contrib.orchestration import ServiceController


class BannedIPController(ServiceController):
    """ Unban IP with fai2ban """
    verbose_name = "BannedIP"
    model = 'websites.BannedIP'
    script_executable = '/usr/bin/python3'
    
    def prepare(self):
        self.append(textwrap.dedent(""))

    def commit(self):
        self.append(textwrap.dedent(""))

    def save(self, content):
        context = self.get_context(content)
        self.append(textwrap.dedent("""
            import subprocess
            import sys
            import ast
            import ipaddress               

            def ejecutar_comando(comando):
                try:
                    resultado = subprocess.run(
                        comando,
                        shell=True, 
                        check=False,              # No lanza excepción si falla
                        text=True,                # Devuelve strings en lugar de bytes
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    )
                    return {
                        'salida': resultado.stdout.strip(),
                        'error': resultado.stderr.strip(),
                        'codigo': resultado.returncode
                    }
                except Exception as e:
                    return {
                        'salida': '',
                        'error': str(e),
                        'codigo': -1
                    }

            def convertir_a_lista(objeto_str):
                try:
                    lista = ast.literal_eval(objeto_str)
                    return lista
                except Exception as e:
                    print(f"Error al convertir: {e}", file=sys.stderr)
                    return []

            resultado = ejecutar_comando("fail2ban-client banned")

            salida = convertir_a_lista(resultado['salida'])
            for x in salida:
                for jail, list_ips in x.items():
                    if  "%(ip)s" in list_ips:
                        print("la Ip %(ip)s esta baneada")
                        print(f"causa: {jail}")
                        orden = ejecutar_comando(f"fail2ban-client set {jail} unbanip %(ip)s")
                        if not orden['error']:
                            print("la ip %(ip)s a sido desbaneada")
                        else:
                            print(f"Error: {orden['error']}", file=sys.stderr)            
                        sys.exit(orden['codigo'])

            if resultado['error']:
                print(f"Error: {resultado['error']}", file=sys.stderr)
            sys.exit(resultado['codigo'])
            """) % context
        )
    
    def get_context(self, content):
        context = {
            'ip': content.ip,
        }
        return context