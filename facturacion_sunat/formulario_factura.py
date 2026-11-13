"""Conversión de los datos del formulario a los modelos de facturación."""

from datetime import date
from decimal import Decimal
import re

from .modelos import Adquirente, Detalle, Emisor, Factura
from .reglas_sunat import _validar_decimal, _validar_texto, validar_ruc


def leer_producto(descripcion: str, cantidad: str, valor_unitario: str) -> Detalle:
    descripcion = descripcion.strip()
    _validar_texto(descripcion, "Descripción", 500)
    importes = []
    for texto, campo, escala in (
        (cantidad, "Cantidad", 3),
        (valor_unitario, "Valor unitario", 10),
    ):
        if not re.fullmatch(r"[0-9]+(?:[.,][0-9]+)?", texto.strip()):
            raise ValueError(f"{campo}: escribe un número decimal sin separador de miles.")
        valor = Decimal(texto.strip().replace(",", "."))
        _validar_decimal(valor, campo, escala)
        importes.append(valor)
    return Detalle(descripcion, *importes)


def crear_factura(
    *, ruc_emisor: str, razon_emisor: str, establecimiento: str,
    ruc_adquirente: str, razon_adquirente: str, serie: str, correlativo: str,
    fecha: str, leyenda: str, productos: tuple[Detalle, ...],
) -> Factura:
    for ruc, campo in ((ruc_emisor, "RUC del emisor"), (ruc_adquirente, "RUC del adquirente")):
        try:
            validar_ruc(ruc.strip())
        except ValueError as error:
            raise ValueError(f"{campo}: {error}") from error
    _validar_texto(razon_emisor.strip(), "Razón social del emisor", 1500)
    _validar_texto(razon_adquirente.strip(), "Razón social del adquirente", 1500)
    if not re.fullmatch(r"[0-9]{1,8}", correlativo.strip()):
        raise ValueError("Correlativo: escribe de uno a ocho dígitos.")
    try:
        if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", fecha.strip()):
            raise ValueError()
        fecha_emision = date.fromisoformat(fecha.strip())
    except ValueError as error:
        raise ValueError("Fecha de emisión: escribe una fecha válida en formato AAAA-MM-DD.") from error
    if len(productos) > 999:
        raise ValueError("La factura admite hasta 999 líneas de producto.")
    return Factura(
        emisor=Emisor(ruc_emisor.strip(), razon_emisor.strip(), establecimiento.strip()),
        adquirente=Adquirente(ruc_adquirente.strip(), razon_adquirente.strip()),
        serie=serie.strip().upper(),
        correlativo=int(correlativo),
        fecha_emision=fecha_emision,
        detalles=tuple(productos),
        leyenda_importe=leyenda.strip(),
    )
