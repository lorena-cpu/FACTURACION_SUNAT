"""Coordina la lectura y validación local sin depender de una interfaz."""

from dataclasses import dataclass
from pathlib import Path
import re

from lxml import etree

from .validacion_xsd import EsquemaNoDisponible, validar_xsd
from .verificacion_xml import FueraDelPerfil, verificar_perfil


XSD_OFICIAL = (
    Path(__file__).resolve().parents[1]
    / "schemas" / "Archivos XSD" / "2.1" / "maindoc" / "UBL-Invoice-2.1.xsd"
)


@dataclass(frozen=True)
class Resultado:
    xsd: str
    perfil: str
    categoria: str
    descripcion: str
    codigo: str = ""
    elemento: str = ""


def validar_factura(xml: Path, xsd: Path = XSD_OFICIAL) -> Resultado:
    try:
        raiz = validar_xsd(xml, xsd)
    except EsquemaNoDisponible as error:
        return Resultado("No disponible", "Sin evaluar", "Configuración del XSD", str(error))
    except OSError as error:
        return Resultado("Sin evaluar", "Sin evaluar", "Lectura del archivo", str(error))
    except ValueError as error:
        causa = error.__cause__
        if isinstance(causa, (etree.XMLSyntaxError, etree.DocumentInvalid)):
            entrada = causa.error_log.last_error
            if entrada is not None:
                ubicacion = entrada.path or ""
                if entrada.line:
                    ubicacion = f"{ubicacion} (línea {entrada.line})".strip()
                return Resultado("Rechazado", "Sin evaluar", "Error XSD o XML", entrada.message, elemento=ubicacion)
        return Resultado("No disponible", "Sin evaluar", "Configuración del XSD", str(error))

    try:
        verificar_perfil(raiz)
    except FueraDelPerfil as error:
        return Resultado("Aprobado", "Fuera del perfil", "Documento fuera del perfil", str(error))
    except ValueError as error:
        mensaje = str(error)
        regla = re.fullmatch(
            r"(?:(cac:InvoiceLine\[\d+\]) \| )?SUNAT ([0-9]{4}) \| (.+?): (.+)",
            mensaje,
            flags=re.DOTALL,
        )
        if regla:
            linea, codigo, elemento, descripcion = regla.groups()
            ruta = f"{linea}/{elemento}" if linea else elemento
            return Resultado("Aprobado", "Rechazado", "Regla SUNAT", descripcion, codigo, ruta)
        return Resultado("Aprobado", "Rechazado", "Control local", mensaje)

    return Resultado("Aprobado", "Aprobado", "Validación local aprobada", "")
