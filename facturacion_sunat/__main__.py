import argparse
from pathlib import Path
import sys

from .ejemplo import factura_ejemplo
from .serializador import generar_xml
from .validacion_xsd import EsquemaNoDisponible, validar_xsd
from .verificacion_xml import verificar_perfil


def main() -> int:
    parser = argparse.ArgumentParser(description="Factura UBL 2.1 académica sin firma")
    comandos = parser.add_subparsers(dest="comando", required=True)
    generar = comandos.add_parser("generar", help="Generar la factura de ejemplo")
    generar.add_argument("--output", type=Path, default=Path("output"))
    validar = comandos.add_parser("validar-xsd", help="Validar con el XSD oficial local")
    validar.add_argument("xml", type=Path)
    validar.add_argument("--xsd", type=Path, required=True)
    verificar = comandos.add_parser(
        "verificar-perfil", help="Verificar el XSD y los controles del perfil académico"
    )
    verificar.add_argument("xml", type=Path)
    verificar.add_argument("--xsd", type=Path, required=True)
    args = parser.parse_args()

    try:
        if args.comando == "generar":
            factura = factura_ejemplo()
            contenido = generar_xml(factura)
            args.output.mkdir(parents=True, exist_ok=True)
            ruta = args.output / f"{factura.emisor.ruc}-01-{factura.identificador}.xml"
            ruta.write_bytes(contenido)
            print(f"XML académico sin firma: {ruta.resolve()}")
            print(f"Total: PEN {factura.totales.importe_a_pagar:.2f}")
            return 0

        raiz = validar_xsd(args.xml, args.xsd)
        print("XSD válido. Resultado estructural, sin evaluación de aceptación tributaria.")
        if args.comando == "verificar-perfil":
            verificar_perfil(raiz)
            print("Controles del perfil académico aprobados. Matriz oficial pendiente de cotejo.")
        return 0
    except EsquemaNoDisponible as error:
        print(f"Validación XSD pendiente. {error}", file=sys.stderr)
        return 2
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
