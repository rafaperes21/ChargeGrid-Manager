"""Integracao de energia do simulador - reexporta a formula unica de trapezio.

Movida para `app/services/energy_integration.py` (M3), reaproveitada tambem pelo motor de
sessao, para nao duplicar a formula entre simulador e backend real.
"""

from app.services.energy_integration import trapezoidal_energy_kwh

__all__ = ["trapezoidal_energy_kwh"]
