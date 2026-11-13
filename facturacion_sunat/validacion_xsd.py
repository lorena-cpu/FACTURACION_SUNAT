"""Validación estructural con el paquete SUNAT incorporado manualmente."""

from pathlib import Path


class EsquemaNoDisponible(Exception):
    """El paquete oficial aún no está disponible en la ruta indicada."""


def validar_xsd(xml: Path, xsd: Path):
    """Devuelve la raíz del mismo documento que superó el esquema."""
    if not xsd.is_file():
        raise EsquemaNoDisponible(f"Falta el XSD de Invoice en {xsd}. Consulta schemas/README.md.")
    try:
        from lxml import etree
    except ImportError as error:
        raise ValueError("Instala lxml con python -m pip install -r requirements.txt.") from error

    try:
        parser = etree.XMLParser(no_network=True, resolve_entities=False, load_dtd=False)
        esquema = etree.XMLSchema(etree.parse(str(xsd), parser))
    except (OSError, etree.LxmlError) as error:
        raise EsquemaNoDisponible(f"No se pudo cargar el XSD oficial: {error}") from error

    try:
        documento = etree.parse(str(xml), parser)
        esquema.assertValid(documento)
        return documento.getroot()
    except etree.LxmlError as error:
        raise ValueError(str(error)) from error
