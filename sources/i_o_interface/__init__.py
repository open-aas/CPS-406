"""
UserEntrypoint do pacote IOInterface.

O loader do faaster procura a classe `IOInterface` neste pacote.
Este módulo funciona como dispatcher: lê `context.registry.aas_id_short`
e instancia o handler correto para cada estação.

Para adicionar uma nova estação:
  1. Crie sources/i_o_interface/{station}_io.py com a classe {Station}IOInterface
  2. Importe abaixo e adicione a entrada em _HANDLERS.
"""

from faaster.extensions.interfaces import ISubmodelExtension
from faaster.extensions.context import SubmodelContext

from .mag_front_io import MagFrontIOInterface
from .meas_io      import MeasIOInterface
from .mag_back_io  import MagBackIOInterface
from .idrill_io    import IDrillIOInterface
from .mpress_io    import MPressIOInterface
from .out_io       import OutIOInterface

# ── Mapa aas_id_short → handler ───────────────────────────────────────────────
_HANDLERS = {
    "aas_station_magfront": MagFrontIOInterface,
    "aas_station_meas":     MeasIOInterface,
    "aas_station_magback":  MagBackIOInterface,
    "aas_station_idrill":   IDrillIOInterface,
    "aas_station_mpress":   MPressIOInterface,
    "aas_station_out":      OutIOInterface,
}


class IOInterface(ISubmodelExtension):
    """
    Dispatcher — roteia para o handler específico da estação em execução.
    O faaster carrega este módulo automaticamente para o submodelo IOInterface.
    """

    def __init__(self, context: SubmodelContext) -> None:
        aas_id = context.registry.aas_id_short
        handler_cls = _HANDLERS.get(aas_id)

        if handler_cls is None:
            known = list(_HANDLERS)
            raise RuntimeError(
                f"IOInterface: nenhum handler registrado para AAS '{aas_id}'. "
                f"Cadastrados: {known}"
            )

        self._handler: ISubmodelExtension = handler_cls(context)

    async def init(self) -> None:
        await self._handler.init()

    async def stop(self) -> None:
        await self._handler.stop()
