"""Controles locales para el perfil académico de venta interna gravada."""

from datetime import date
from decimal import Decimal
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .modelos import Factura


def validar_ruc(ruc: str) -> None:
    if not isinstance(ruc, str) or not re.fullmatch(r"(?:10|15|16|17|20)[0-9]{9}", ruc):
        raise ValueError("El RUC debe tener 11 dígitos y un prefijo admitido.")
    pesos = (5, 4, 3, 2, 7, 6, 5, 4, 3, 2)
    suma = sum(int(digito) * peso for digito, peso in zip(ruc[:10], pesos))
    if (11 - suma % 11) % 10 != int(ruc[-1]):
        raise ValueError("El dígito verificador del RUC es incorrecto.")


def _validar_texto(texto: str, campo: str, maximo: int) -> None:
    if not isinstance(texto, str) or not texto.strip() or len(texto) > maximo:
        raise ValueError(f"{campo} debe contener entre 1 y {maximo} caracteres.")
    if re.search(r"[^\x09\x0A\x0D\x20-\uD7FF\uE000-\uFFFD\U00010000-\U0010FFFF]", texto):
        raise ValueError(f"{campo} contiene caracteres inválidos para XML 1.0.")


def _validar_decimal(valor: Decimal, campo: str, escala: int) -> None:
    if not isinstance(valor, Decimal) or not valor.is_finite():
        raise ValueError(f"{campo} debe ser un Decimal finito.")
    if not Decimal("0") < valor < Decimal("1000000000000"):
        raise ValueError(f"{campo} está fuera del intervalo positivo del perfil.")
    if valor.as_tuple().exponent < -escala:
        raise ValueError(f"{campo} admite hasta {escala} decimales en este perfil.")


def validar_datos(factura: "Factura") -> None:
    if not isinstance(factura.serie, str) or not re.fullmatch(r"F[A-Z0-9]{3}", factura.serie):
        raise ValueError("La serie debe empezar con F y tener cuatro caracteres alfanuméricos.")
    if type(factura.correlativo) is not int or not 1 <= factura.correlativo <= 99_999_999:
        raise ValueError("El correlativo debe ser un entero positivo de hasta ocho dígitos.")
    if type(factura.fecha_emision) is not date:
        raise ValueError("La fecha de emisión debe ser de tipo date.")
    for parte in (factura.emisor, factura.adquirente):
        validar_ruc(parte.ruc)
        _validar_texto(parte.razon_social, "Razón social", 1500)
    if not isinstance(factura.emisor.establecimiento, str) or not re.fullmatch(
        r"[0-9]{4}", factura.emisor.establecimiento
    ):
        raise ValueError("El código de establecimiento debe tener cuatro dígitos.")
    _validar_texto(factura.leyenda_importe, "Leyenda del importe", 200)
    if not factura.detalles:
        raise ValueError("Se requiere al menos una línea.")
    for linea in factura.detalles:
        _validar_texto(linea.descripcion, "Descripción", 500)
        _validar_decimal(linea.cantidad, "Cantidad", 3)
        _validar_decimal(linea.valor_unitario, "Valor unitario", 10)
