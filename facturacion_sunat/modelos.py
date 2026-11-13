"""Modelo para venta interna gravada, al contado y en soles."""

from dataclasses import dataclass, field
from datetime import date
from decimal import Context, Decimal, ROUND_HALF_UP, localcontext


IGV = Decimal("18")
CENTIMO = Decimal("0.01")
LIMITE_MONETARIO = Decimal("1000000000000")


def redondear(valor: Decimal) -> Decimal:
    return valor.quantize(CENTIMO, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class Emisor:
    ruc: str
    razon_social: str
    establecimiento: str = "0000"


@dataclass(frozen=True)
class Adquirente:
    ruc: str
    razon_social: str


@dataclass(frozen=True)
class Detalle:
    descripcion: str
    cantidad: Decimal
    valor_unitario: Decimal


@dataclass(frozen=True)
class Tributos:
    base: Decimal
    importe: Decimal


@dataclass(frozen=True)
class Totales:
    valor_venta: Decimal
    igv: Decimal
    importe_con_impuestos: Decimal
    importe_a_pagar: Decimal


@dataclass(frozen=True)
class Factura:
    emisor: Emisor
    adquirente: Adquirente
    serie: str
    correlativo: int
    fecha_emision: date
    detalles: tuple[Detalle, ...]
    leyenda_importe: str
    tributos_linea: tuple[Tributos, ...] = field(init=False)
    precios_con_igv: tuple[Decimal, ...] = field(init=False)
    totales: Totales = field(init=False)

    def __post_init__(self) -> None:
        # La factura conserva una instantánea de las líneas usadas en el cálculo.
        object.__setattr__(self, "detalles", tuple(self.detalles))
        from .reglas_sunat import validar_datos

        validar_datos(self)
        with localcontext(Context(prec=40)):
            bases = tuple(
                redondear(linea.cantidad * linea.valor_unitario)
                for linea in self.detalles
            )
            tributos = tuple(
                Tributos(base, redondear(base * IGV / 100)) for base in bases
            )
            precios = tuple(
                (linea.valor_unitario * (1 + IGV / 100)).quantize(
                    Decimal("0.0000000001"), rounding=ROUND_HALF_UP
                ).normalize()
                for linea in self.detalles
            )
            valor_venta = sum(bases, Decimal("0.00"))
            # Factura2_0, fila 351: calcular el IGV global sobre las bases declaradas.
            igv = redondear(valor_venta * IGV / 100)
            total = valor_venta + igv

        if any(base <= 0 for base in bases):
            raise ValueError("Cada línea debe tener una base gravada positiva al céntimo.")
        if total >= LIMITE_MONETARIO or any(precio >= LIMITE_MONETARIO for precio in precios):
            raise ValueError("El importe excede el límite monetario del perfil.")
        object.__setattr__(self, "tributos_linea", tributos)
        object.__setattr__(self, "precios_con_igv", precios)
        object.__setattr__(self, "totales", Totales(valor_venta, igv, total, total))

    @property
    def identificador(self) -> str:
        return f"{self.serie}-{self.correlativo}"
