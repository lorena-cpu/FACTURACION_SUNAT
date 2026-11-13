from datetime import date
from decimal import Decimal

from .modelos import Adquirente, Detalle, Emisor, Factura


def factura_ejemplo() -> Factura:
    return Factura(
        emisor=Emisor("20999999001", "Emisor Ficticio de Pruebas S.A.C."),
        adquirente=Adquirente("20999999019", "Adquirente Ficticio de Pruebas S.A.C."),
        serie="F001",
        correlativo=1,
        fecha_emision=date(2026, 11, 12),
        detalles=(
            Detalle("Cuaderno A4 & separadores", Decimal("2"), Decimal("55.00")),
            Detalle("Archivador de cartón", Decimal("3"), Decimal("30.00")),
        ),
        leyenda_importe="DOSCIENTOS TREINTA Y SEIS CON 00/100 SOLES",
    )
